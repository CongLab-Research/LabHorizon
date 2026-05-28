from __future__ import annotations

import json
import unittest
from typing import Any

from agents.client import ChatResult
from agents.workflow import solve_row


class FakeClient:
    def __init__(self, phase: str) -> None:
        self.phase = phase
        self.calls: list[list[dict[str, Any]]] = []

    def complete(self, messages: list[dict[str, Any]], *, temperature: float | None = None) -> ChatResult:
        self.calls.append(messages)
        if self.phase == "actor":
            if "Level 2" in str(messages):
                content = "```python\nstep1 = mix_sample(sample=sample, duration_min=2)\n```"
            else:
                content = "The protocol state supports the first candidate.\nFinal Next Action: A"
        elif "transition" in str(messages[0].get("content")).lower():
            content = json.dumps(
                {
                    "action_id": "a1",
                    "next_state": "candidate reaches the target state",
                    "satisfied_constraints": ["matches target"],
                    "missing_or_violated_constraints": [],
                    "risk_notes": [],
                }
            )
        elif "selector" in str(messages[0].get("content")).lower():
            content = json.dumps({"selected_action_id": "a1", "ranked_action_ids": ["a1"], "explanation": "best"})
        else:
            content = json.dumps(
                {
                    "current_state": "sample is ready",
                    "target_state": "sample is mixed",
                    "key_constraints": ["duration"],
                }
            )
        return ChatResult(content=content, model_returned=f"fake-{self.phase}", usage=None, latency_s=0.0)


class AgentWorkflowTests(unittest.TestCase):
    def test_level1_actor_simulator_selector(self) -> None:
        row = {
            "id": "LabHorizon-L1-test-000001",
            "asset": [],
            "historical_actions": "The sample is ready for mixing.",
            "candidate_next_actions": ["mix_sample(sample=sample, duration_min=2)", "discard_sample(sample=sample)"],
            "next_action": "mix_sample(sample=sample, duration_min=2)",
        }
        result = solve_row(
            level=1,
            row=row,
            actor=FakeClient("actor"),
            simulator=FakeClient("simulator"),
            selector=FakeClient("selector"),
            samples=1,
            sample_concurrency=1,
            transition_concurrency=1,
            actor_temperature=0.7,
            simulator_temperature=None,
            selector_temperature=None,
        )
        self.assertTrue(result["correct"])
        self.assertEqual(result["predicted_next_action"], row["next_action"])

    def test_level2_actor_simulator_selector(self) -> None:
        row = {
            "id": "LabHorizon-L2-test-000001",
            "context": "A sample must be mixed.",
            "goal": "Mix the sample.",
            "constraints": ["Mix for 2 min."],
            "available_inputs": '[{"name": "sample", "description": "input sample"}]',
            "action_pool_names": ["mix_sample"],
            "action_pool": "def mix_sample(sample, duration_min):\n    pass\n",
            "gold_action_sequence": "step1 = mix_sample(sample=sample, duration_min=2)",
        }
        result = solve_row(
            level=2,
            row=row,
            actor=FakeClient("actor"),
            simulator=FakeClient("simulator"),
            selector=FakeClient("selector"),
            samples=1,
            sample_concurrency=1,
            transition_concurrency=1,
            actor_temperature=0.7,
            simulator_temperature=None,
            selector_temperature=None,
        )
        self.assertEqual(result["metrics"]["final_score"], 1.0)
        self.assertIn("mix_sample", result["predicted_action_sequence"])


if __name__ == "__main__":
    unittest.main()
