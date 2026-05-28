from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from evaluation.level1.prompts import build_level1_messages, parse_final_next_action
from evaluation.utils import (
    OpenAICompatibleClient,
    default_cache_dir,
    default_data_root,
    env_required,
    load_cache,
    load_dotenv,
    load_level_dataset,
    response_text,
    row_id,
    write_jsonl,
)


def evaluate_row(
    row: dict[str, Any],
    *,
    client: OpenAICompatibleClient,
    model: str,
    temperature: float | None,
) -> dict[str, Any]:
    response = client.chat_completion(model=model, messages=build_level1_messages(row), temperature=temperature)
    text = response_text(response)
    prediction = parse_final_next_action(text, row["candidate_next_actions"])
    gold = str(row["next_action"]).strip()
    return {
        "id": row_id(row),
        "gold_next_action": gold,
        "predicted_next_action": prediction,
        "correct": prediction == gold,
        "response": text,
        "model_returned": response.get("model"),
    }


def summarize(rows: list[dict[str, Any]]) -> dict[str, Any]:
    if not rows:
        return {"count": 0}
    correct = sum(1 for row in rows if row.get("correct"))
    invalid = sum(1 for row in rows if row.get("predicted_next_action") is None)
    return {
        "count": len(rows),
        "next_action_accuracy": correct / len(rows),
        "correct": correct,
        "invalid": invalid,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate a model on LabHorizon Level 1.")
    parser.add_argument("--split", choices=["train", "test"], default="test")
    parser.add_argument("--data-root", type=Path, default=default_data_root())
    parser.add_argument("--cache-dir", type=Path, default=default_cache_dir())
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--limit", type=int)
    parser.add_argument("--resume", action="store_true")
    parser.add_argument("--temperature", type=float)
    parser.add_argument("--timeout", type=float, default=120.0)
    parser.add_argument("--retries", type=int, default=2)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    load_dotenv()
    client = OpenAICompatibleClient(
        base_url=env_required("BASE_URL"),
        api_key=env_required("API_KEY"),
        timeout=args.timeout,
        retries=args.retries,
    )
    dataset = load_level_dataset(level=1, split=args.split, data_root=args.data_root, cache_dir=args.cache_dir)
    if args.limit is not None:
        dataset = dataset.select(range(min(args.limit, len(dataset))))

    cache = load_cache(args.output) if args.resume else {}
    results: list[dict[str, Any]] = list(cache.values())
    seen = set(cache)

    for index, row in enumerate(dataset, start=1):
        identifier = row_id(row)
        if identifier in seen:
            print(f"[{index}/{len(dataset)}] cached {identifier}", flush=True)
            continue
        print(f"[{index}/{len(dataset)}] evaluating {identifier}", flush=True)
        result = evaluate_row(row, client=client, model=args.model, temperature=args.temperature)
        results.append(result)
        write_jsonl(args.output, results)

    summary = summarize(results)
    summary_path = args.output.with_suffix(args.output.suffix + ".summary.json")
    summary_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps(summary, indent=2, ensure_ascii=False), file=sys.stdout)


if __name__ == "__main__":
    main()
