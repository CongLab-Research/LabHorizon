from __future__ import annotations

import json
from typing import Any

from evaluation.utils import available_inputs_text, constraints_text


def raw_input_names(row: dict[str, Any]) -> set[str]:
    try:
        items = json.loads(row.get("available_inputs") or "[]")
    except json.JSONDecodeError:
        return set()
    names = {str(item.get("name")) for item in items if isinstance(item, dict) and item.get("name")}
    return names


def build_level2_messages(row: dict[str, Any]) -> list[dict[str, str]]:
    prompt = (
        "You are solving a LabHorizon Level 2 long-horizon experimental planning task.\n"
        "Use only the provided action pool and raw inputs. You may explain briefly, but the final output must include "
        "a Python fenced block with straight-line assignment statements calling action-pool functions.\n\n"
        f"Context:\n{row['context']}\n\n"
        f"Goal:\n{row['goal']}\n\n"
        f"Constraints:\n{constraints_text(row['constraints'])}\n\n"
        f"Available inputs:\n{available_inputs_text(row['available_inputs'])}\n\n"
        f"Action pool:\n```python\n{row['action_pool']}\n```\n"
    )
    return [
        {"role": "system", "content": "You are a careful scientific experimental planning assistant."},
        {"role": "user", "content": prompt},
    ]
