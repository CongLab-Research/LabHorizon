from __future__ import annotations

import unittest
from typing import Any

from evaluation.level1.evaluate import evaluate_row as evaluate_level1_row
from evaluation.level1.evaluate import summarize as summarize_level1
from evaluation.level2.evaluate import evaluate_row as evaluate_level2_row
from evaluation.level2.evaluate import summarize as summarize_level2


class FakeCompletionClient:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict[str, Any]] = []

    def chat_completion(
        self,
        *,
        model: str,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
    ) -> dict[str, Any]:
        self.calls.append({"model": model, "messages": messages, "temperature": temperature})
        return {
            "model": f"fake-{model}",
            "choices": [{"message": {"content": self.content}}],
        }


class EvaluationTests(unittest.TestCase):
    def test_level1_evaluate_row_scores_exact_next_action(self) -> None:
        row = {
            "id": "LabHorizon-L1-test-000001",
            "asset": [],
            "historical_actions": "The sample is ready for mixing.",
            "candidate_next_actions": [
                "mix_sample(sample=sample, duration_min=2)",
                "discard_sample(sample=sample)",
            ],
            "next_action": "mix_sample(sample=sample, duration_min=2)",
        }
        result = evaluate_level1_row(
            row,
            client=FakeCompletionClient("Reasoning.\nFinal Next Action: A"),
            model="fake-model",
            temperature=None,
        )
        self.assertTrue(result["correct"])
        self.assertEqual(result["predicted_next_action"], row["next_action"])
        self.assertEqual(summarize_level1([result])["next_action_accuracy"], 1.0)

    def test_level2_evaluate_row_scores_ast_metrics(self) -> None:
        gold = "mixed = mix_sample(sample=sample, duration_min=2)"
        row = {
            "id": "LabHorizon-L2-test-000001",
            "context": "A sample must be mixed.",
            "goal": "Mix the sample.",
            "constraints": ["Mix for 2 min."],
            "available_inputs": '[{"name": "sample", "description": "input sample"}]',
            "action_pool_names": ["mix_sample"],
            "action_pool": "def mix_sample(sample, duration_min):\n    pass\n",
            "gold_action_sequence": gold,
        }
        result = evaluate_level2_row(
            row,
            client=FakeCompletionClient(f"```python\n{gold}\n```"),
            model="fake-model",
            temperature=None,
        )
        self.assertIsNone(result["parse_error"])
        self.assertEqual(result["metrics"]["final_score"], 1.0)
        self.assertEqual(summarize_level2([result])["final_score"], 1.0)


if __name__ == "__main__":
    unittest.main()
