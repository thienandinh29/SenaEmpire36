import asyncio

import pytest

from app.content.models import Item, ModelIdentity
from app.guardrails.answerability import verify_item
from app.tutor.hints import HintDraft, hint, release_hint, verify_hint
from tests.content.fakes import FakeGateway, topic


def prepared() -> tuple[FakeGateway, Item]:
    fake = FakeGateway()
    item = asyncio.run(verify_item(fake.item, fake.chunks, fake))
    return fake, item


def test_unverified_question_never_gets_hint() -> None:
    fake = FakeGateway()
    sources, _, _, _ = topic()
    assert (
        asyncio.run(hint(fake.item, 1, None, fake.chunks, "pro", gateway=fake, sources=sources))
        is None
    )
    assert fake.calls == []


def test_verified_hint_payload_has_citations_and_no_internal_metadata() -> None:
    fake, item = prepared()
    sources, _, _, _ = topic()
    result = asyncio.run(
        hint(
            item,
            2,
            "wrong-choice",
            fake.chunks,
            "pro",
            gateway=fake,
            sources=sources,
            history=["Em đang phân vân."],
        )
    )
    assert result is not None
    assert set(result.model_dump()) == {"hint_vi", "citations"}
    assert result.citations[0].chunk_id == item.chunk_ids[0]
    assert result.citations[0].source_id in item.source_ids


@pytest.mark.parametrize(
    "field",
    [
        "supported",
        "no_answer_leak",
        "no_elimination",
        "relevant_to_history",
        "clear_vietnamese",
        "level_appropriate",
    ],
)
def test_bad_hint_rubric_is_never_released(field: str) -> None:
    fake, item = prepared()
    fake.overrides = {field: False}
    sources, _, _, _ = topic()
    assert (
        asyncio.run(hint(item, 1, None, fake.chunks, "pro", gateway=fake, sources=sources)) is None
    )


def test_literal_answer_blocks_before_model_call() -> None:
    fake, item = prepared()
    draft = HintDraft(hint_vi="Đáp án là 2.", chunk_ids=item.chunk_ids)
    before = len(fake.calls)
    generator = ModelIdentity(
        provider="fake", model="fake", family="gemini", identity_source="gateway"
    )
    attempt = asyncio.run(verify_hint(item, draft, fake.chunks, generator, fake, level=1))
    assert attempt.verification.status == "needs_review"
    assert len(fake.calls) == before


def test_hint_same_family_and_changed_history_block_release() -> None:
    fake, item = prepared()
    sources, _, _, _ = topic()
    generator = ModelIdentity(
        provider="fake", model="fake", family="claude", identity_source="gateway"
    )
    draft = HintDraft(hint_vi="Hãy xác định phép toán trong đề.", chunk_ids=item.chunk_ids)
    failed = asyncio.run(verify_hint(item, draft, fake.chunks, generator, fake, level=1))
    assert failed.verification.status == "needs_review"
    generator = generator.model_copy(update={"family": "gemini"})
    attempt = asyncio.run(
        verify_hint(item, draft, fake.chunks, generator, fake, level=1, history=["Gợi ý trước"])
    )
    assert attempt.verification.status == "verified"
    assert release_hint(attempt, item, fake.chunks, sources, level=1, history=[]) is None
    assert (
        release_hint(attempt, item, fake.chunks, sources, level=2, history=["Gợi ý trước"]) is None
    )
