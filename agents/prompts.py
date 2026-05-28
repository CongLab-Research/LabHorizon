from __future__ import annotations

import json
from typing import Any

from evaluation.level1.prompts import build_level1_messages
from evaluation.level2.prompts import build_level2_messages
from evaluation.utils import candidate_action_lines, constraints_text


def actor_messages(level: int, row: dict[str, Any], *, sample_index: int, sample_count: int) -> list[dict[str, Any]]:
    if level == 1:
        messages = build_level1_messages(row)
        messages.append(
            {
                "role": "user",
                "content": (
                    f"This is Actor sample {sample_index}/{sample_count}. "
                    "Reason independently, then finish with Final Next Action: X."
                ),
            }
        )
        return messages
    messages = build_level2_messages(row)
    messages.append(
        {
            "role": "user",
            "content": (
                f"This is Actor sample {sample_index}/{sample_count}. "
                "Generate one complete structured action sequence."
            ),
        }
    )
    return messages


def compact_task_text(level: int, row: dict[str, Any]) -> str:
    if level == 1:
        return (
            f"Historical actions and current state:\n{row['historical_actions']}\n\n"
            f"Candidate next actions:\n{candidate_action_lines(row['candidate_next_actions'])}"
        )
    return (
        f"Context:\n{row['context']}\n\n"
        f"Goal:\n{row['goal']}\n\n"
        f"Constraints:\n{constraints_text(row['constraints'])}\n\n"
        f"Available inputs:\n{row['available_inputs']}\n\n"
        f"Action pool:\n```python\n{row['action_pool']}\n```"
    )


def simulator_state_messages(level: int, row: dict[str, Any]) -> list[dict[str, Any]]:
    prompt = (
        "Construct the structured experimental state for a LabHorizon Actor-Simulator-Selector run. "
        "The Simulator is a state checker for high-level laboratory actions, not a physical robot simulator. "
        "Do not solve the task directly.\n\n"
        "Return a JSON object with keys:\n"
        "- current_state: concise state before the next action or action sequence\n"
        "- target_state: concise state that a correct prediction should reach\n"
        "- key_constraints: array of important protocol constraints\n\n"
        f"Task:\n{compact_task_text(level, row)}"
    )
    return [
        {"role": "system", "content": "You are the Simulator stage of LabHorizon. Return JSON only."},
        {"role": "user", "content": prompt},
    ]


def transition_messages(
    *,
    level: int,
    row: dict[str, Any],
    state: dict[str, Any],
    candidate: dict[str, Any],
) -> list[dict[str, Any]]:
    prompt = (
        "Evaluate one Actor candidate by predicting the experimental state it would produce. "
        "Do not choose the final candidate here.\n\n"
        "Return a JSON object with keys:\n"
        "- action_id\n"
        "- next_state\n"
        "- satisfied_constraints\n"
        "- missing_or_violated_constraints\n"
        "- risk_notes\n\n"
        f"Current state:\n{state.get('current_state', '')}\n\n"
        f"Target state:\n{state.get('target_state', '')}\n\n"
        f"Task:\n{compact_task_text(level, row)}\n\n"
        f"Candidate:\n{json.dumps(candidate, ensure_ascii=False, indent=2)}"
    )
    return [
        {"role": "system", "content": "You are the Simulator transition checker for LabHorizon. Return JSON only."},
        {"role": "user", "content": prompt},
    ]


def selector_messages(
    *,
    state: dict[str, Any],
    candidates: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    prompt = (
        "Select the Actor candidate whose predicted state best satisfies the LabHorizon target state. "
        "Prefer candidates with fewer missing constraints, fewer structural validation errors, and better protocol consistency.\n\n"
        "Return a JSON object with keys:\n"
        "- selected_action_id\n"
        "- ranked_action_ids\n"
        "- explanation\n\n"
        f"Target state:\n{state.get('target_state', '')}\n\n"
        f"Candidates:\n{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        f"Simulator transitions:\n{json.dumps(transitions, ensure_ascii=False, indent=2)}"
    )
    return [
        {"role": "system", "content": "You are the Selector stage of LabHorizon. Return JSON only."},
        {"role": "user", "content": prompt},
    ]
