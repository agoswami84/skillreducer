from __future__ import annotations

import os
from unittest.mock import patch

import pytest

from skillreducer.config import (
    Config,
    load_dotenv,
    resolve_api_base_url,
    resolve_api_key,
    resolve_compression_model,
    resolve_routing_model,
)
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
    monkeypatch.delenv("compression_model", raising=False)
    monkeypatch.delenv("compression", raising=False)
    monkeypatch.delenv("routing_model", raising=False)
    monkeypatch.delenv("routing_oracle", raising=False)
    monkeypatch.delenv("evaluation_model", raising=False)
    monkeypatch.delenv("evaluation", raising=False)


def test_load_dotenv_finds_env_in_parent_directory(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    work = tmp_path / "nested" / "run"
    work.mkdir(parents=True)
    (tmp_path / ".env").write_text("api_key=parent-key\n", encoding="utf-8")
    monkeypatch.chdir(work)
    monkeypatch.delenv("api_key", raising=False)

    load_dotenv(force=True)

    assert os.environ.get("api_key") == "parent-key"


def test_load_dotenv_cwd_overrides_parent(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    work = tmp_path / "nested" / "run"
    work.mkdir(parents=True)
    (tmp_path / ".env").write_text("api_key=parent-key\n", encoding="utf-8")
    (work / ".env").write_text("api_key=cwd-key\n", encoding="utf-8")
    monkeypatch.chdir(work)
    monkeypatch.delenv("api_key", raising=False)

    load_dotenv(force=True)

    assert os.environ.get("api_key") == "cwd-key"


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


def test_resolve_model_ids_prefers_environment_over_config() -> None:
    config = Config(
        compression_model="yaml-compression",
        routing_model="yaml-routing",
        evaluation_model="yaml-evaluation",
    )
    with patch.dict(
        os.environ,
        {
            "compression_model": "env-compression",
            "routing_model": "env-routing",
            "evaluation_model": "env-evaluation",
        },
    ):
        assert resolve_compression_model(config) == "env-compression"
        assert resolve_routing_model(config) == "env-routing"


def test_config_load_merges_env_model_ids(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "models:\n"
        "  compression: yaml-compression\n"
        "  routing_oracle: yaml-routing\n"
        "  evaluation: yaml-evaluation\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("compression_model", "env-compression")
    monkeypatch.setenv("routing_model", "env-routing")
    monkeypatch.setenv("evaluation_model", "env-evaluation")

    config = Config.load(config_path)

    assert config.compression_model == "env-compression"
    assert config.routing_model == "env-routing"
    assert config.evaluation_model == "env-evaluation"


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
    assert captured[0]["id"] == "compression-model"
    assert captured[1]["id"] == "compression-model"
    assert captured[2]["id"] == "routing-model"
    assert captured[3]["id"] == "evaluation-model"
    for kwargs in captured:
        assert kwargs["api_key"] == "shared-env-key"
        assert kwargs["base_url"] == "https://shared.example/v1"


def test_agents_use_env_model_ids_over_config() -> None:
    config = Config(
        api_key="test-key",
        compression_model="yaml-compression",
        routing_model="yaml-routing",
        evaluation_model="yaml-evaluation",
    )
    captured: list[dict] = []

    class FakeOpenAIChat:
        def __init__(self, **kwargs) -> None:
            captured.append(kwargs)

    with patch.dict(
        os.environ,
        {
            "compression_model": "env-compression",
            "routing_model": "env-routing",
            "evaluation_model": "env-evaluation",
        },
    ):
        with patch("skillreducer.model.OpenAIChat", FakeOpenAIChat):
            create_compression_model(config)
            create_routing_model(config)
            create_evaluation_model(config)

    assert [kwargs["id"] for kwargs in captured] == [
        "env-compression",
        "env-routing",
        "env-evaluation",
    ]


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
