import asyncio

from pydantic import BaseModel

from app.llm.gateway import (
    Attempt,
    Gateway,
    complete_with_metadata,
    gateway_scope,
    verification_scope,
)
from tests.llm.test_gateway import Fake, routes


def test_rejected_paid_outputs_are_observed() -> None:
    class Answer(BaseModel):
        count: int

    attempts: list[Attempt] = []
    fake = Fake(["invalid JSON", '{"count":2}'])
    gateway = Gateway(routes(), {"vertex": fake}, observe_attempt=attempts.append)
    result = asyncio.run(
        gateway.complete_with_metadata(
            "items",
            "free",
            "s",
            [{"role": "user", "content": "q"}],
            Answer,
        )
    )
    assert result.value == Answer(count=2)
    assert [a.status for a in attempts] == ["validation_error", "success"]
    assert sum(a.input_tokens for a in attempts) == 20
    assert sum(a.output_tokens for a in attempts) == 10


def test_public_gateway_entry_point_uses_job_scope() -> None:
    fake = Fake(["generated", "verified"])
    gateway = Gateway(routes(), {"vertex": fake, "bedrock": fake})

    async def run() -> None:
        with gateway_scope(gateway):
            generated = await complete_with_metadata(
                "items", "free", "system", [{"role": "user", "content": "q"}]
            )
            with verification_scope(generated.route.family):
                verified = await complete_with_metadata(
                    "verify", "free", "blind", [{"role": "user", "content": "cited chunks"}]
                )
                assert generated.route.family != verified.route.family

    asyncio.run(run())
    assert fake.models == ["gemini-test", "claude-test"]
