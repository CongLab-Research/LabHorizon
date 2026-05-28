from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

from evaluation.level1.prompts import parse_final_next_action
from evaluation.level2.metrics import compare_steps, extract_python_steps, parse_steps
from evaluation.level2.prompts import raw_input_names
from evaluation.utils import row_id

from .client import AgentClient
from .parsing import candidate_label, extract_json_object
from .prompts import actor_messages, selector_messages, simulator_state_messages, transition_messages


def parse_actor_candidate(level: int, row: dict[str, Any], text: str, *, action_id: str) -> dict[str, Any]:
    if level == 1:
        action = parse_final_next_action(text, row["candidate_next_actions"])
        if action is None:
            raise ValueError("Actor response did not contain a parseable final next action")
        return {
            "action_id": action_id,
            "candidate_label": candidate_label(action, row["candidate_next_actions"]),
            "next_action": action,
            "response": text,
        }
    program = extract_python_steps(text)
    steps = parse_steps(program)
    action_pool = set(row.get("action_pool_names") or [])
    unknown_actions = sorted({step.action for step in steps if action_pool and step.action not in action_pool})
    return {
        "action_id": action_id,
        "action_sequence": program,
        "step_count": len(steps),
        "unknown_actions": unknown_actions,
        "response": text,
    }


def sample_actor_candidates(
    *,
    level: int,
    row: dict[str, Any],
    actor: AgentClient,
    samples: int,
    sample_concurrency: int,
    temperature: float | None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    def sample_once(index: int) -> tuple[dict[str, Any] | None, dict[str, Any]]:
        action_id = f"a{index}"
        try:
            response = actor.complete(
                actor_messages(level, row, sample_index=index, sample_count=samples),
                temperature=temperature,
            )
            candidate = parse_actor_candidate(level, row, response.content, action_id=action_id)
            candidate["model_returned"] = response.model_returned
            candidate["latency_s"] = response.latency_s
            return candidate, {"action_id": action_id, "ok": True}
        except Exception as exc:  # noqa: BLE001
            return None, {"action_id": action_id, "ok": False, "error": str(exc)}

    candidates: list[dict[str, Any]] = []
    diagnostics: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(samples, sample_concurrency))) as executor:
        futures = [executor.submit(sample_once, index) for index in range(1, samples + 1)]
        for future in as_completed(futures):
            candidate, diagnostic = future.result()
            diagnostics.append(diagnostic)
            if candidate is not None:
                candidates.append(candidate)
    candidates.sort(key=lambda item: item["action_id"])
    diagnostics.sort(key=lambda item: item["action_id"])
    if not candidates:
        raise RuntimeError(f"all Actor samples failed: {diagnostics}")
    return candidates, diagnostics


def simulator_state(level: int, row: dict[str, Any], simulator: AgentClient, *, temperature: float | None) -> dict[str, Any]:
    response = simulator.complete(simulator_state_messages(level, row), temperature=temperature)
    try:
        state = extract_json_object(response.content)
    except Exception:
        state = {"current_state": response.content, "target_state": "", "key_constraints": []}
    state["model_returned"] = response.model_returned
    state["latency_s"] = response.latency_s
    return state


def simulate_transitions(
    *,
    level: int,
    row: dict[str, Any],
    simulator: AgentClient,
    state: dict[str, Any],
    candidates: list[dict[str, Any]],
    transition_concurrency: int,
    temperature: float | None,
) -> list[dict[str, Any]]:
    def transition_once(candidate: dict[str, Any]) -> dict[str, Any]:
        response = simulator.complete(
            transition_messages(level=level, row=row, state=state, candidate=candidate),
            temperature=temperature,
        )
        try:
            parsed = extract_json_object(response.content)
        except Exception:
            parsed = {"action_id": candidate["action_id"], "next_state": response.content}
        parsed["action_id"] = str(parsed.get("action_id") or candidate["action_id"])
        parsed["model_returned"] = response.model_returned
        parsed["latency_s"] = response.latency_s
        return parsed

    transitions: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=max(1, min(len(candidates), transition_concurrency))) as executor:
        futures = [executor.submit(transition_once, candidate) for candidate in candidates]
        for future in as_completed(futures):
            transitions.append(future.result())
    transitions.sort(key=lambda item: item.get("action_id", ""))
    return transitions


def select_candidate(
    *,
    selector: AgentClient,
    state: dict[str, Any],
    candidates: list[dict[str, Any]],
    transitions: list[dict[str, Any]],
    temperature: float | None,
) -> tuple[dict[str, Any], dict[str, Any]]:
    response = selector.complete(
        selector_messages(state=state, candidates=candidates, transitions=transitions),
        temperature=temperature,
    )
    try:
        selection = extract_json_object(response.content)
    except Exception:
        selection = {"selected_action_id": candidates[0]["action_id"], "explanation": response.content}
    selected_id = str(selection.get("selected_action_id") or "")
    selected = next((candidate for candidate in candidates if candidate["action_id"] == selected_id), candidates[0])
    selection["model_returned"] = response.model_returned
    selection["latency_s"] = response.latency_s
    return selected, selection


def score_selected(level: int, row: dict[str, Any], selected: dict[str, Any]) -> dict[str, Any]:
    if level == 1:
        prediction = selected["next_action"]
        gold = str(row["next_action"]).strip()
        return {
            "predicted_next_action": prediction,
            "gold_next_action": gold,
            "correct": prediction == gold,
        }
    gold_steps = parse_steps(row["gold_action_sequence"])
    pred_steps = parse_steps(selected["action_sequence"])
    metrics = compare_steps(gold_steps, pred_steps, raw_inputs=raw_input_names(row))
    return {
        "predicted_action_sequence": selected["action_sequence"],
        "gold_action_sequence": row["gold_action_sequence"],
        "metrics": metrics,
    }


def solve_row(
    *,
    level: int,
    row: dict[str, Any],
    actor: AgentClient,
    simulator: AgentClient,
    selector: AgentClient,
    samples: int,
    sample_concurrency: int,
    transition_concurrency: int,
    actor_temperature: float | None,
    simulator_temperature: float | None,
    selector_temperature: float | None,
) -> dict[str, Any]:
    candidates, actor_diagnostics = sample_actor_candidates(
        level=level,
        row=row,
        actor=actor,
        samples=samples,
        sample_concurrency=sample_concurrency,
        temperature=actor_temperature,
    )
    state = simulator_state(level, row, simulator, temperature=simulator_temperature)
    transitions = simulate_transitions(
        level=level,
        row=row,
        simulator=simulator,
        state=state,
        candidates=candidates,
        transition_concurrency=transition_concurrency,
        temperature=simulator_temperature,
    )
    selected, selection = select_candidate(
        selector=selector,
        state=state,
        candidates=candidates,
        transitions=transitions,
        temperature=selector_temperature,
    )
    result = {
        "id": row_id(row),
        "selected_action_id": selected["action_id"],
        "actor_candidates": candidates,
        "actor_diagnostics": actor_diagnostics,
        "simulator_state": state,
        "simulator_transitions": transitions,
        "selection": selection,
    }
    result.update(score_selected(level, row, selected))
    return result
