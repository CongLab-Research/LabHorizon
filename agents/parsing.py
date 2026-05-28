from __future__ import annotations

import json
import re
from typing import Any


def extract_json_object(text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        parsed = json.loads(text[start : end + 1])
        if isinstance(parsed, dict):
            return parsed
    raise ValueError("response does not contain a JSON object")


def label_for_index(index: int) -> str:
    return chr(ord("A") + index)


def candidate_label(action: str, candidates: list[str]) -> str | None:
    normalized = action.strip()
    for index, candidate in enumerate(candidates):
        if candidate.strip() == normalized:
            return label_for_index(index)
    return None


def strip_fenced_json(text: str) -> str:
    match = re.search(r"```(?:json)?\s*(.*?)```", text, flags=re.IGNORECASE | re.DOTALL)
    return match.group(1).strip() if match else text.strip()
