from __future__ import annotations

import os
import unittest

from agents.client import AgentClient
from agents.workflow import solve_row
from evaluation.level1.evaluate import evaluate_row as evaluate_level1_row
from evaluation.level2.evaluate import evaluate_row as evaluate_level2_row
from evaluation.utils import OpenAICompatibleClient, load_dotenv, load_level_dataset


def api_tests_enabled() -> bool:
    load_dotenv()
    return (
        os.environ.get("RUN_LABHORIZON_API_TESTS") == "1"
        and bool(os.environ.get("BASE_URL"))
        and bool(os.environ.get("API_KEY"))
        and bool(os.environ.get("EVAL_MODEL"))
    )


@unittest.skipUnless(api_tests_enabled(), "set RUN_LABHORIZON_API_TESTS=1 and OpenAI-compatible API env vars")
class ApiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.eval_model = os.environ["EVAL_MODEL"]
        cls.actor_model = os.environ.get("ACTOR_MODEL", cls.eval_model)
        cls.simulator_model = os.environ.get("SIMULATOR_MODEL", cls.eval_model)
        cls.selector_model = os.environ.get("SELECTOR_MODEL", cls.simulator_model)
        cls.base_url = os.environ["BASE_URL"]
        cls.api_key = os.environ["API_KEY"]

    def test_level1_real_api_one_sample(self) -> None:
        dataset = load_level_dataset(level=1, split="test")
        client = OpenAICompatibleClient(base_url=self.base_url, api_key=self.api_key, timeout=180.0, retries=1)
        result = evaluate_level1_row(dataset[0], client=client, model=self.eval_model, temperature=None)
        self.assertEqual(result["id"], dataset[0]["id"])
        self.assertIn("response", result)
        self.assertIn("model_returned", result)

    def test_level2_real_api_one_sample(self) -> None:
        dataset = load_level_dataset(level=2, split="test")
        client = OpenAICompatibleClient(base_url=self.base_url, api_key=self.api_key, timeout=180.0, retries=1)
        result = evaluate_level2_row(dataset[0], client=client, model=self.eval_model, temperature=None)
        self.assertEqual(result["id"], dataset[0]["id"])
        self.assertIn("metrics", result)
        self.assertIn("final_score", result["metrics"])

    def test_agent_real_api_one_level2_sample(self) -> None:
        dataset = load_level_dataset(level=2, split="test")
        actor = AgentClient(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.actor_model,
            timeout=180.0,
            retries=1,
        )
        simulator = AgentClient(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.simulator_model,
            timeout=180.0,
            retries=1,
        )
        selector = AgentClient(
            base_url=self.base_url,
            api_key=self.api_key,
            model=self.selector_model,
            timeout=180.0,
            retries=1,
        )
        result = solve_row(
            level=2,
            row=dataset[0],
            actor=actor,
            simulator=simulator,
            selector=selector,
            samples=1,
            sample_concurrency=1,
            transition_concurrency=1,
            actor_temperature=0.7,
            simulator_temperature=None,
            selector_temperature=None,
        )
        self.assertEqual(result["id"], dataset[0]["id"])
        self.assertIn("metrics", result)


if __name__ == "__main__":
    unittest.main()
