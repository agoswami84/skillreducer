from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATHS = [
    Path("config.yaml"),
    Path.home() / ".config" / "skillreducer" / "config.yaml",
]


@dataclass
class Config:
    compression_model: str = "gpt-4o-mini"
    routing_model: str = "gpt-4o-mini"
    evaluation_model: str = "gpt-4o-mini"
    api_key: str | None = None
    base_url: str | None = None
    short_description_tokens: int = 40
    min_reference_tokens: int = 30
    max_feedback_iterations: int = 2
    max_restore_steps: int = 3
    num_test_queries: int = 8
    use_llm: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        candidates = [path] if path else DEFAULT_CONFIG_PATHS
        data: dict = {}
        for candidate in candidates:
            if candidate and candidate.exists():
                loaded = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                models = loaded.get("models", {})
                thresholds = loaded.get("thresholds", {})
                oracle = loaded.get("oracle", {})
                data = {
                    "compression_model": models.get("compression", cls.compression_model),
                    "routing_model": models.get("routing_oracle", cls.routing_model),
                    "evaluation_model": models.get("evaluation", cls.evaluation_model),
                    "api_key": loaded.get("api_key"),
                    "base_url": loaded.get("base_url"),
                    "short_description_tokens": thresholds.get(
                        "short_description_tokens", cls.short_description_tokens
                    ),
                    "min_reference_tokens": thresholds.get(
                        "min_reference_tokens", cls.min_reference_tokens
                    ),
                    "max_feedback_iterations": thresholds.get(
                        "max_feedback_iterations", cls.max_feedback_iterations
                    ),
                    "max_restore_steps": thresholds.get(
                        "max_restore_steps", cls.max_restore_steps
                    ),
                    "num_test_queries": oracle.get("num_test_queries", cls.num_test_queries),
                    "use_llm": loaded.get("use_llm", True),
                }
                break
        return cls(**data)
