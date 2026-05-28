from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from evaluation.utils import OpenAICompatibleClient, response_text


@dataclass(frozen=True)
class ChatResult:
    content: str
    model_returned: str | None
    usage: Any
    latency_s: float


class AgentClient:
    def __init__(self, *, base_url: str, api_key: str, model: str, timeout: float, retries: int) -> None:
        self.model = model
        self.client = OpenAICompatibleClient(base_url=base_url, api_key=api_key, timeout=timeout, retries=retries)

    def complete(self, messages: list[dict[str, Any]], *, temperature: float | None = None) -> ChatResult:
        started = time.time()
        response = self.client.chat_completion(model=self.model, messages=messages, temperature=temperature)
        content = response_text(response)
        if not content.strip():
            raise RuntimeError("model returned empty message content")
        return ChatResult(
            content=content,
            model_returned=response.get("model"),
            usage=response.get("usage"),
            latency_s=round(time.time() - started, 3),
        )


def prefixed_or_base_env(prefix: str, name: str, environ: dict[str, str]) -> str:
    return environ.get(f"{prefix}_{name}") or environ.get(name) or ""
