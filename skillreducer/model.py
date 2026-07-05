"""Agno model factory for SkillReducer LLM calls."""

from __future__ import annotations

from typing import TYPE_CHECKING

from skillreducer.config import (
    Config,
    resolve_api_base_url,
    resolve_api_key,
    resolve_compression_model,
    resolve_evaluation_model,
    resolve_routing_model,
)

if TYPE_CHECKING:
    from agno.models.base import Model

try:
    from agno.models.openai import OpenAIChat
except ImportError:  # pragma: no cover - optional at type-check time
    OpenAIChat = None  # type: ignore[misc, assignment]


def create_openai_chat(
    config: Config,
    *,
    model_id: str | None = None,
    temperature: float = 0.0,
) -> Model:
    """Build an Agno OpenAI-compatible chat model from SkillReducer config."""
    if OpenAIChat is None:
        raise ImportError("agno is not installed. Install with: pip install agno")

    api_key = resolve_api_key(config)
    if not api_key:
        raise ValueError(
            "No API key found. Set api_key in the environment, .env, or config.yaml."
        )

    kwargs: dict = {
        "id": model_id or resolve_compression_model(config),
        "api_key": api_key,
        "temperature": temperature,
    }
    base_url = resolve_api_base_url(config)
    if base_url:
        kwargs["base_url"] = base_url
    return OpenAIChat(**kwargs)


def create_compression_model(config: Config) -> Model:
    return create_openai_chat(config, model_id=resolve_compression_model(config))


def create_routing_model(config: Config) -> Model:
    return create_openai_chat(config, model_id=resolve_routing_model(config))


def create_evaluation_model(config: Config) -> Model:
    return create_openai_chat(config, model_id=resolve_evaluation_model(config))
