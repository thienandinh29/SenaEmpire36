import asyncio
from collections.abc import Sequence

import pytest
from pydantic import BaseModel

from app.llm.gateway import (
    Gateway,
    GatewayError,
    Message,
    ProviderError,
    ProviderReply,
    Route,
    Routing,
    load_routing,
    verification_scope,
)


class Answer(BaseModel):
    count: int


def test_unknown_generator_family_rejected() -> None:
    with pytest.raises(ValueError, match="family"), verification_scope("unknown"):
        pass


class Fake:
    def __init__(self, replies: list[str | Exception]) -> None:
        self.replies = replies
        self.models: list[str] = []

    async def generate(
        self,
        route: Route,
        system: str,
        messages: Sequence[Message],
        schema: type[BaseModel] | None,
    ) -> ProviderReply:
        self.models.append(route.model)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return ProviderReply(reply, 10, 5)


def routes() -> Routing:
    primary = Route(provider="vertex", model="gemini-test", family="gemini")
    fallback = Route(provider="bedrock", model="claude-test", family="claude")
    return Routing(tiers={"free": {"items": [primary, fallback], "verify": [primary, fallback]}})


def test_invalid_json_retries_then_falls_back() -> None:
    fake = Fake(["not json", '{"count":"invalid"}', '{"count":3}'])
    result = asyncio.run(
        Gateway(routes(), {"vertex": fake, "bedrock": fake}).complete_with_metadata(
            "items",
            "free",
            "system",
            [{"role": "user", "content": "hi"}],
            Answer,
        )
    )
    assert result.value == Answer(count=3)
    assert result.route.family == "claude"
    assert result.input_tokens == 10
    assert fake.models == ["gemini-test", "gemini-test", "claude-test"]


def test_verifier_excludes_actual_fallback_generator_and_resets_scope() -> None:
    fake = Fake(['{"count":1}'])
    gateway = Gateway(routes(), {"vertex": fake, "bedrock": fake})
    with verification_scope("claude"):
        asyncio.run(gateway.complete("verify", "free", "s", [{"role": "user", "content": "q"}]))
    assert fake.models == ["gemini-test"]
    with pytest.raises(GatewayError, match="verification_scope"):
        asyncio.run(gateway.complete("verify", "free", "s", [{"role": "user", "content": "q"}]))


def test_permanent_failure_skips_retry() -> None:
    fake = Fake([ProviderError("credentials_missing"), "ok"])
    result = asyncio.run(
        Gateway(routes(), {"vertex": fake, "bedrock": fake}).complete(
            "items", "free", "s", [{"role": "user", "content": "q"}]
        )
    )
    assert result == "ok"
    assert len(fake.models) == 2


def test_default_routing_disallows_free_research() -> None:
    gateway = Gateway(load_routing(), {})
    with pytest.raises(GatewayError, match="No route"):
        asyncio.run(gateway.complete("research", "free", "s", [{"role": "user", "content": "q"}]))


def test_total_timeout_cancels_request() -> None:
    class Slow(Fake):
        async def generate(
            self,
            route: Route,
            system: str,
            messages: Sequence[Message],
            schema: type[BaseModel] | None,
        ) -> ProviderReply:
            await asyncio.sleep(10)
            return ProviderReply("late")

    gateway = Gateway(routes(), {"vertex": Slow([])}, total_timeout=0.01)
    with pytest.raises(GatewayError, match="deadline"):
        asyncio.run(gateway.complete("items", "free", "s", [{"role": "user", "content": "q"}]))


def test_no_eligible_verifier_fails_closed() -> None:
    routing = routes()
    routing.tiers["free"]["verify"] = routing.tiers["free"]["verify"][:1]
    with verification_scope("gemini"), pytest.raises(GatewayError, match="No eligible"):
        asyncio.run(
            Gateway(routing, {}).complete("verify", "free", "s", [{"role": "user", "content": "q"}])
        )


def test_environment_model_and_family_mismatch(monkeypatch: pytest.MonkeyPatch) -> None:
    route = Route(provider="vertex", model="${P3_TEST_MODEL}", family="gemini")
    routing = Routing(tiers={"free": {"items": [route]}})
    monkeypatch.setenv("P3_TEST_MODEL", "claude-test")
    with pytest.raises(GatewayError, match="family_mismatch"):
        asyncio.run(
            Gateway(routing, {}).complete("items", "free", "s", [{"role": "user", "content": "q"}])
        )
