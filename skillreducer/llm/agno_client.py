"""Agno agent adapter for pipeline LLM calls."""

from __future__ import annotations

import json
from typing import Any

try:
    from agno.agent import Agent
except ImportError:  # pragma: no cover
    Agent = None  # type: ignore[misc, assignment]


class AgnoLLMClient:
    """Expose complete/complete_json so stage modules can call an Agno agent."""

    def __init__(self, agent: Agent) -> None:
        self._agent = agent
        self._enabled = True

    @property
    def enabled(self) -> bool:
        return self._enabled

    def complete(self, prompt: str, model: str | None = None, system: str | None = None) -> str:
        message = f"{system}\n\n{prompt}" if system else prompt
        run = self._agent.run(message)
        content = run.content
        if content is None:
            return ""
        return content.strip() if isinstance(content, str) else str(content).strip()

    def complete_json(self, prompt: str, model: str | None = None, system: str | None = None) -> Any:
        text = self.complete(prompt, model=model, system=system)
        text = text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        return json.loads(text)
