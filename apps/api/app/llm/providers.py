"""Vertex REST, Bedrock Converse and OpenRouter adapters; no secrets in errors."""

import asyncio
import importlib
import os
from collections.abc import Sequence
from typing import Any
from urllib.parse import quote

import httpx
from pydantic import BaseModel

from app.llm.gateway import (
    Gateway,
    Message,
    ProviderError,
    ProviderReply,
    Route,
    load_routing,
    schema_instruction,
)


async def _post(url: str, token: str, payload: dict[str, Any]) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(timeout=30, trust_env=False) as client:
            response = await client.post(
                url, headers={"Authorization": f"Bearer {token}"}, json=payload
            )
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict):
                raise ValueError("Expected response object")
            return data
    except httpx.HTTPStatusError as exc:
        status = exc.response.status_code
        raise ProviderError(
            f"http_{status}", retryable=status in (408, 429) or status >= 500
        ) from None
    except (httpx.RequestError, ValueError):
        raise ProviderError("transport_or_json_error", retryable=True) from None


class VertexAdapter:
    @staticmethod
    def _token() -> str:
        try:
            auth = importlib.import_module("google.auth")
            request = importlib.import_module("google.auth.transport.urllib3")
            credentials, _ = auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
            credentials.refresh(request.Request())
            return str(credentials.token)
        except Exception:
            raise ProviderError("vertex_credentials_unavailable") from None

    async def generate(
        self,
        route: Route,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel] | None,
    ) -> ProviderReply:
        project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
        location = os.environ.get("VERTEX_LOCATION", "asia-southeast1")
        if not project:
            raise ProviderError("vertex_project_missing")
        host = (
            "aiplatform.googleapis.com"
            if location == "global"
            else (f"{quote(location, safe='')}-aiplatform.googleapis.com")
        )
        url = (
            f"https://{host}/v1/projects/{quote(project, safe='')}/locations/"
            f"{quote(location, safe='')}/publishers/google/models/"
            f"{quote(route.model, safe='')}:generateContent"
        )
        payload: dict[str, Any] = {
            "systemInstruction": {"parts": [{"text": schema_instruction(system, schema)}]},
            "contents": [
                {
                    "role": "model" if m.role == "assistant" else "user",
                    "parts": [{"text": m.content}],
                }
                for m in messages
            ],
            "generationConfig": {"maxOutputTokens": 4096},
        }
        if schema:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        data = await _post(url, await asyncio.to_thread(self._token), payload)
        try:
            candidate = data["candidates"][0]
            if candidate.get("finishReason") != "STOP":
                raise ProviderError("vertex_incomplete_response", retryable=True)
            text = "".join(p.get("text", "") for p in candidate["content"]["parts"])
            usage = data.get("usageMetadata", {})
            return ProviderReply(
                text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0)
            )
        except (KeyError, IndexError, TypeError):
            raise ProviderError("vertex_invalid_response", retryable=True) from None


class BedrockAdapter:
    @staticmethod
    def _converse(route: Route, system: str, messages: Sequence[Message]) -> ProviderReply:
        try:
            boto3 = importlib.import_module("boto3")
            config = importlib.import_module("botocore.config")
            session = boto3.Session(profile_name=os.environ.get("AWS_PROFILE") or None)
            client = session.client(
                "bedrock-runtime",
                region_name=os.environ.get("AWS_REGION", "ap-southeast-1"),
                config=config.Config(
                    connect_timeout=5, read_timeout=25, retries={"total_max_attempts": 1}
                ),
            )
            try:
                data = client.converse(
                    modelId=route.model,
                    system=[{"text": system}],
                    messages=[{"role": m.role, "content": [{"text": m.content}]} for m in messages],
                    inferenceConfig={"maxTokens": 4096},
                )
            finally:
                client.close()
            if data.get("stopReason") != "end_turn":
                raise ProviderError("bedrock_incomplete_response", retryable=True)
            text = "".join(p.get("text", "") for p in data["output"]["message"]["content"])
            usage = data.get("usage", {})
            return ProviderReply(text, usage.get("inputTokens", 0), usage.get("outputTokens", 0))
        except ProviderError:
            raise
        except Exception as exc:
            response = getattr(exc, "response", {})
            code = response.get("Error", {}).get("Code", "bedrock_unavailable")
            raise ProviderError(
                code,
                retryable=code
                in {
                    "ThrottlingException",
                    "ServiceUnavailableException",
                    "ModelTimeoutException",
                    "InternalServerException",
                },
            ) from None

    async def generate(
        self,
        route: Route,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel] | None,
    ) -> ProviderReply:
        return await asyncio.to_thread(
            self._converse, route, schema_instruction(system, schema), messages
        )


class OpenRouterAdapter:
    async def generate(
        self,
        route: Route,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel] | None,
    ) -> ProviderReply:
        token = os.environ.get("OPENROUTER_API_KEY", "")
        if not token:
            raise ProviderError("openrouter_key_missing")
        data = await _post(
            "https://openrouter.ai/api/v1/chat/completions",
            token,
            {
                "model": route.model,
                "max_tokens": 4096,
                "messages": [
                    {"role": "system", "content": schema_instruction(system, schema)},
                    *[m.model_dump() for m in messages],
                ],
            },
        )
        try:
            choice = data["choices"][0]
            if choice.get("finish_reason") != "stop":
                raise ProviderError("openrouter_incomplete_response", retryable=True)
            text = choice["message"]["content"]
            if not isinstance(text, str):
                raise TypeError
            usage = data.get("usage", {})
            return ProviderReply(
                text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
            )
        except (KeyError, IndexError, TypeError):
            raise ProviderError("openrouter_invalid_response", retryable=True) from None


def default_gateway() -> Gateway:
    return Gateway(
        load_routing(),
        {
            "vertex": VertexAdapter(),
            "bedrock": BedrockAdapter(),
            "openrouter": OpenRouterAdapter(),
        },
    )
