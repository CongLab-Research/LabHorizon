from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any

from evaluation.utils import (
    default_cache_dir,
    default_data_root,
    env_required,
    load_cache,
    load_dotenv,
    load_level_dataset,
    row_id,
    write_jsonl,
)

from .client import AgentClient, prefixed_or_base_env
from .workflow import solve_row


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the LabHorizon Actor-Simulator-Selector agent.")
    parser.add_argument("--level", type=int, choices=(1, 2), required=True)
    parser.add_argument("--split", choices=["train", "test"], default="test")
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    parser.add_argument("--actor-model", help="Actor model ID. Defaults to ACTOR_MODEL from .env or the environment.")
    parser.add_argument("--simulator-model", help="Simulator model ID. Defaults to SIMULATOR_MODEL, then actor model.")
    parser.add_argument("--selector-model", help="Selector model ID. Defaults to SELECTOR_MODEL, then simulator model.")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--samples", type=int, default=4)
    parser.add_argument("--concurrency", type=int, default=1)
    parser.add_argument("--sample-concurrency", type=int, default=4)
    parser.add_argument("--transition-concurrency", type=int, default=4)
    parser.add_argument("--actor-temperature", type=float, default=0.7)
    parser.add_argument("--simulator-temperature", type=float)
    parser.add_argument("--selector-temperature", type=float)
    parser.add_argument("--timeout", type=float, default=180.0)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args()


def make_client(prefix: str, *, model: str, timeout: float, retries: int) -> AgentClient:
    base_url = prefixed_or_base_env(prefix, "BASE_URL", os.environ)
    api_key = prefixed_or_base_env(prefix, "API_KEY", os.environ)
    if not base_url:
        base_url = env_required("BASE_URL")
    if not api_key:
        api_key = env_required("API_KEY")
    return AgentClient(base_url=base_url, api_key=api_key, model=model, timeout=timeout, retries=retries)


def summarize(level: int, rows: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {"level": level, "count": len(rows)}
    if not rows:
        return summary
    if level == 1:
        correct = sum(1 for row in rows if row.get("correct"))
        summary.update({"next_action_accuracy": correct / len(rows), "correct": correct})
        return summary
    keys = ["action_sequence_similarity", "parameter_accuracy", "final_score"]
    for key in keys:
        values = [float(row["metrics"][key]) for row in rows if row.get("metrics") and key in row["metrics"]]
        if values:
            summary[key] = sum(values) / len(values)
    return summary


def main() -> None:
    args = parse_args()
    load_dotenv()
    actor_model = args.actor_model or env_required("ACTOR_MODEL")
    simulator_model = args.simulator_model or os.environ.get("SIMULATOR_MODEL") or actor_model
    selector_model = args.selector_model or os.environ.get("SELECTOR_MODEL") or simulator_model
    actor = make_client("ACTOR", model=actor_model, timeout=args.timeout, retries=args.retries)
    simulator = make_client("SIMULATOR", model=simulator_model, timeout=args.timeout, retries=args.retries)
    selector = make_client("SELECTOR", model=selector_model, timeout=args.timeout, retries=args.retries)

    dataset = load_level_dataset(level=args.level, split=args.split, data_root=args.data_root, cache_dir=args.cache_dir)
    if args.limit is not None:
        dataset = dataset.select(range(min(args.limit, len(dataset))))

    cache = load_cache(args.output) if args.resume else {}
    results: list[dict[str, Any]] = list(cache.values())
    seen = set(cache)

    pending = [(index, row) for index, row in enumerate(dataset, start=1) if row_id(row) not in seen]

    def solve(index: int, row: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        identifier = row_id(row)
        result = solve_row(
            level=args.level,
            row=row,
            actor=actor,
            simulator=simulator,
            selector=selector,
            samples=args.samples,
            sample_concurrency=args.sample_concurrency,
            transition_concurrency=args.transition_concurrency,
            actor_temperature=args.actor_temperature,
            simulator_temperature=args.simulator_temperature,
            selector_temperature=args.selector_temperature,
        )
        return index, result

    with ThreadPoolExecutor(max_workers=max(1, args.concurrency)) as executor:
        futures = {executor.submit(solve, index, row): row_id(row) for index, row in pending}
        completed: dict[int, dict[str, Any]] = {}
        for future in as_completed(futures):
            identifier = futures[future]
            try:
                index, result = future.result()
            except Exception as exc:  # noqa: BLE001
                result = {"id": identifier, "error": str(exc)}
                index = len(completed) + 1
            completed[index] = result
            merged = results + [completed[idx] for idx in sorted(completed)]
            write_jsonl(args.output, merged)
            print(f"[{len(merged)}/{len(dataset)}] {result.get('id')}", flush=True)

    final_rows = results + [completed[idx] for idx in sorted(completed)]
    summary = summarize(args.level, final_rows)
    args.output.with_suffix(args.output.suffix + ".summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stdout)


if __name__ == "__main__":
    main()
