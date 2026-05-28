from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from datasets import Dataset, load_dataset


LEVEL1_REPO_DIR = "LabHorizon-3D-Asset-Perception"
LEVEL2_REPO_DIR = "LabHorizon-Protocol-Conditioned-Planning"


def load_dotenv(path: Path = Path(".env")) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def env_required(name: str) -> str:
    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def normalize_base_url(base_url: str) -> str:
    return base_url.rstrip("/")


class OpenAICompatibleClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 120.0, retries: int = 2) -> None:
        self.base_url = normalize_base_url(base_url)
        self.api_key = api_key
        self.timeout = timeout
        self.retries = retries

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
    ) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if temperature is not None:
            payload["temperature"] = temperature

        body = json.dumps(payload).encode("utf-8")
        url = f"{self.base_url}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        last_error: Exception | None = None
        for attempt in range(self.retries + 1):
            request = urllib.request.Request(url, data=body, headers=headers, method="POST")
            try:
                with urllib.request.urlopen(request, timeout=self.timeout) as response:
                    return json.loads(response.read().decode("utf-8"))
            except urllib.error.HTTPError as exc:
                text = exc.read().decode("utf-8", errors="replace")
                last_error = RuntimeError(f"HTTP {exc.code}: {text[:1000]}")
            except Exception as exc:  # noqa: BLE001
                last_error = exc
            if attempt < self.retries:
                time.sleep(2**attempt)

        assert last_error is not None
        raise last_error


def response_text(response: dict[str, Any]) -> str:
    choices = response.get("choices") or []
    if not choices:
        return ""
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text", "")))
        return "\n".join(parts)
    return ""


def default_data_root() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return (repo_root / "../../data").resolve()


def default_cache_dir() -> Path:
    repo_root = Path(__file__).resolve().parents[1]
    return repo_root / ".cache" / "huggingface" / "datasets"


def parquet_files(dataset_dir: Path, split: str) -> list[str]:
    files = sorted((dataset_dir / "data").glob(f"{split}-*.parquet"))
    if not files:
        raise FileNotFoundError(f"No parquet files found for split={split!r} under {dataset_dir / 'data'}")
    return [str(path) for path in files]


def load_level_dataset(
    *,
    level: int,
    split: str,
    data_root: Path | None = None,
    cache_dir: Path | None = None,
) -> Dataset:
    root = data_root or default_data_root()
    cache = cache_dir or default_cache_dir()
    cache.mkdir(parents=True, exist_ok=True)
    if level == 1:
        dataset_dir = root / LEVEL1_REPO_DIR
    elif level == 2:
        dataset_dir = root / LEVEL2_REPO_DIR
    else:
        raise ValueError(f"Unsupported level: {level}")

    files = parquet_files(dataset_dir, split)
    return load_dataset("parquet", data_files={split: files}, split=split, cache_dir=str(cache))


def candidate_action_lines(candidate_next_actions: list[str]) -> str:
    labels = list("ABCDEFGHIJ")
    return "\n".join(
        f"{label}. {action}" for label, action in zip(labels, candidate_next_actions, strict=False)
    )


def constraints_text(constraints: list[str]) -> str:
    return "\n".join(f"- {item}" for item in constraints)


def available_inputs_text(raw: str) -> str:
    return raw


def row_id(row: dict[str, Any]) -> str:
    return str(row.get("id") or "")


def json_default(value: Any) -> Any:
    if hasattr(value, "item"):
        return value.item()
    return str(value)


def load_cache(path: Path | None) -> dict[str, dict[str, Any]]:
    if path is None or not path.exists():
        return {}
    cache: dict[str, dict[str, Any]] = {}
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("id"):
                cache[str(row["id"])] = row
    return cache


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False, default=json_default) + "\n")
