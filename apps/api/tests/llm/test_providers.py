import asyncio
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from app.llm.gateway import Message, ProviderError, Route
from app.llm.providers import BedrockAdapter, OpenRouterAdapter, VertexAdapter


def test_vertex_payload_and_usage(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    monkeypatch.setenv("VERTEX_LOCATION", "global")
    captured: dict[str, Any] = {}

    async def post(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        captured.update(url=url, token=token, payload=payload)
        return {
            "candidates": [{"finishReason": "STOP", "content": {"parts": [{"text": "ok"}]}}],
            "usageMetadata": {"promptTokenCount": 4, "candidatesTokenCount": 2},
        }

    with (
        patch("app.llm.providers._post", post),
        patch.object(VertexAdapter, "_token", return_value="fake"),
    ):
        reply = asyncio.run(
            VertexAdapter().generate(
                Route(provider="vertex", model="gemini-test", family="gemini"),
                "system",
                [Message(role="user", content="q"), Message(role="assistant", content="a")],
                None,
            )
        )
    assert captured["url"].startswith("https://aiplatform.googleapis.com/v1/projects/test-project/")
    assert captured["payload"]["contents"][1]["role"] == "model"
    assert reply.text == "ok" and reply.input_tokens == 4


def test_openrouter_truncation_is_not_a_success(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake")

    async def post(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {"choices": [{"finish_reason": "length", "message": {"content": "partial"}}]}

    with patch("app.llm.providers._post", post), pytest.raises(ProviderError, match="incomplete"):
        asyncio.run(
            OpenRouterAdapter().generate(
                Route(provider="openrouter", model="anthropic/claude-test", family="claude"),
                "s",
                [Message(role="user", content="q")],
                None,
            )
        )


def test_bedrock_converse_payload_and_client_cleanup(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_REGION", "ap-southeast-1")
    monkeypatch.delenv("AWS_PROFILE", raising=False)
    client = MagicMock()
    client.converse.return_value = {
        "stopReason": "end_turn",
        "output": {"message": {"content": [{"text": "ok"}]}},
        "usage": {"inputTokens": 3, "outputTokens": 1},
    }
    session = MagicMock()
    session.client.return_value = client
    boto3 = SimpleNamespace(Session=MagicMock(return_value=session))
    config = SimpleNamespace(Config=MagicMock(return_value="fake-config"))
    with patch("app.llm.providers.importlib.import_module", side_effect=[boto3, config]):
        reply = asyncio.run(
            BedrockAdapter().generate(
                Route(provider="bedrock", model="claude-test", family="claude"),
                "system",
                [Message(role="user", content="question")],
                None,
            )
        )
    assert reply.text == "ok" and reply.input_tokens == 3
    client.converse.assert_called_once_with(
        modelId="claude-test",
        system=[{"text": "system"}],
        messages=[{"role": "user", "content": [{"text": "question"}]}],
        inferenceConfig={"maxTokens": 4096},
    )
    client.close.assert_called_once()
