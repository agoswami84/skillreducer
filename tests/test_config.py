from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from skillreducer.config import Config, resolve_api_base_url, resolve_api_key
from skillreducer.llm.client import LLMClient
from skillreducer.model import (
    create_compression_model,
    create_evaluation_model,
    create_openai_chat,
    create_routing_model,
)


@pytest.fixture(autouse=True)
def clear_credential_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("api_key", raising=False)
    monkeypatch.delenv("api_base_url", raising=False)


def test_resolve_api_key_prefers_environment_over_config() -> None:
    config = Config(api_key="yaml-key")
    with patch.dict(os.environ, {"api_key": "env-key"}):
        assert resolve_api_key(config) == "env-key"


def test_resolve_api_base_url_prefers_environment_over_config() -> None:
    config = Config(api_base_url="https://yaml.example/v1")
    with patch.dict(os.environ, {"api_base_url": "https://env.example/v1"}):
        assert resolve_api_base_url(config) == "https://env.example/v1"


def test_config_load_merges_env_credentials(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "api_key: yaml-key\napi_base_url: https://yaml.example/v1\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("api_key", "env-key")
    monkeypatch.setenv("api_base_url", "https://env.example/v1")

    config = Config.load(config_path)

    assert config.api_key == "env-key"
    assert config.api_base_url == "https://env.example/v1"
    assert resolve_api_key(config) == "env-key"
    assert resolve_api_base_url(config) == "https://env.example/v1"


def test_all_agents_use_same_resolved_credentials() -> None:
    config = Config(
        api_key="yaml-key-should-not-win",
        api_base_url="https://yaml.example/v1",
        compression_model="compression-model",
        routing_model="routing-model",
        evaluation_model="evaluation-model",
    )
    captured: list[dict] = []

    class FakeOpenAIChat:
        def __init__(self, **kwargs) -> None:
            captured.append(kwargs)

    with patch.dict(
        os.environ,
        {
            "api_key": "shared-env-key",
            "api_base_url": "https://shared.example/v1",
        },
    ):
        with patch("skillreducer.model.OpenAIChat", FakeOpenAIChat):
            create_openai_chat(config)
            create_compression_model(config)
            create_routing_model(config)
            create_evaluation_model(config)

    assert len(captured) == 4
    for kwargs in captured:
        assert kwargs["api_key"] == "shared-env-key"
        assert kwargs["base_url"] == "https://shared.example/v1"


def test_llm_client_uses_same_resolved_credentials() -> None:
    config = Config(api_key="yaml-key", api_base_url="https://yaml.example/v1")

    with patch.dict(
        os.environ,
        {
            "api_key": "shared-env-key",
            "api_base_url": "https://shared.example/v1",
        },
    ):
        with patch("skillreducer.llm.client.OpenAI") as mock_openai:
            LLMClient(config)

    mock_openai.assert_called_once_with(
        api_key="shared-env-key",
        base_url="https://shared.example/v1",
    )
