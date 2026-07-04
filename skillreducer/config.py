from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATHS = [
    Path("config.yaml"),
    Path.home() / ".config" / "skillreducer" / "config.yaml",
]

# Env / .env field names (only these).
_API_KEY_ENV = ("api_key",)
_API_BASE_URL_ENV = ("api_base_url",)


def load_dotenv(path: Path | None = None) -> None:
    """Load KEY=VALUE pairs from a .env file into os.environ (does not override existing)."""
    candidates = [path] if path else [Path(".env"), Path(__file__).resolve().parents[1] / ".env"]
    for candidate in candidates:
        if not candidate or not candidate.is_file():
            continue
        for line in candidate.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'").strip('"')
            if key and key not in os.environ:
                os.environ[key] = value
        break


def resolve_api_key(config: Config | None = None) -> str | None:
    """Resolve API key: config.yaml, then environment variables."""
    if config and config.api_key:
        return config.api_key
    for name in _API_KEY_ENV:
        value = os.environ.get(name)
        if value:
            return value
    return None


def resolve_api_base_url(config: Config | None = None) -> str | None:
    """Resolve API base URL: config.yaml (base_url / api_base_url), then environment."""
    if config:
        if config.api_base_url:
            return config.api_base_url
        if config.base_url:
            return config.base_url
    for name in _API_BASE_URL_ENV:
        value = os.environ.get(name)
        if value:
            return value
    return None


@dataclass
class Config:
    compression_model: str = "gpt-4o-mini"
    routing_model: str = "gpt-4o-mini"
    evaluation_model: str = "gpt-4o-mini"
    api_key: str | None = None
    api_base_url: str | None = None
    base_url: str | None = None  # alias for api_base_url (config.yaml compatibility)
    short_description_tokens: int = 40
    min_reference_tokens: int = 30
    max_feedback_iterations: int = 2
    max_restore_steps: int = 3
    num_test_queries: int = 8
    num_distractors: int = 4
    include_adversarial: bool = True
    use_llm: bool = True

    @classmethod
    def load(cls, path: Path | None = None) -> Config:
        """Load config from yaml (optional), then apply env for api_key / api_base_url."""
        load_dotenv()
        candidates = [path] if path else DEFAULT_CONFIG_PATHS
        data: dict = {}
        for candidate in candidates:
            if candidate and candidate.exists():
                loaded = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
                models = loaded.get("models", {})
                thresholds = loaded.get("thresholds", {})
                oracle = loaded.get("oracle", {})
                api_base = loaded.get("api_base_url") or loaded.get("base_url")
                data = {
                    "compression_model": models.get("compression", cls.compression_model),
                    "routing_model": models.get("routing_oracle", cls.routing_model),
                    "evaluation_model": models.get("evaluation", cls.evaluation_model),
                    "api_key": loaded.get("api_key"),
                    "api_base_url": api_base,
                    "base_url": api_base,
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
                    "num_distractors": oracle.get("num_distractors", cls.num_distractors),
                    "include_adversarial": oracle.get("include_adversarial", cls.include_adversarial),
                    "use_llm": loaded.get("use_llm", True),
                }
                break

        config = cls(**data)
        # Environment overrides yaml for credentials / endpoint.
        env_key = None
        for name in _API_KEY_ENV:
            if os.environ.get(name):
                env_key = os.environ[name]
                break
        if env_key:
            config.api_key = env_key

        env_base = None
        for name in _API_BASE_URL_ENV:
            if os.environ.get(name):
                env_base = os.environ[name]
                break
        if env_base:
            config.api_base_url = env_base
            config.base_url = env_base
        elif config.api_base_url and not config.base_url:
            config.base_url = config.api_base_url
        elif config.base_url and not config.api_base_url:
            config.api_base_url = config.base_url

        return config
