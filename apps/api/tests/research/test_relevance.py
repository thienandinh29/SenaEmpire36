import asyncio
from collections.abc import Sequence
from typing import Any

import httpx
import pytest

from app.content.gateway import ModelReply
from app.research.agent import ChosenSource, ResearchAgent, SearchResult
from app.research.reader import Allowlist, Publisher, SafeReader, SourceError
from app.research.relevance import ResearchRelevance
from tests.content.fakes import FakeGateway


class RelevanceModels(FakeGateway):
    async def generate(self, **kwargs: Any) -> ModelReply:
        self.calls.append(kwargs)
        content: dict[str, Any]
        if kwargs["task"] == "plan_research":
            content = {"query": "beginner English verb be lessons", "scope_vi": "Beginner lesson"}
        elif "candidates" in kwargs["payload"]:
            content = {"urls": [r["url"] for r in kwargs["payload"]["candidates"]]}
        else:
            payload = kwargs["payload"]
            # Content matters even when the title promises the right subject.
            content = {
                "teaches_goal": "English lesson" in payload["page_text"],
                "reason_vi": "Fixture",
                "teaching_quote": payload["page_text"].split("\n")[0],
            }
        return ModelReply(content=content, identity=self.item.generator)


def test_plan_preserves_goal_as_data_and_source_check_uses_actual_content() -> None:
    models = RelevanceModels()
    policy = ResearchRelevance(models)
    plan = asyncio.run(policy.plan("hoc tieng anh"))
    assert plan.query == "beginner English verb be lessons"
    assert models.calls[0]["payload"] == {"learning_goal": "hoc tieng anh"}
    for text, expected in [
        ("English lesson: Use am with I, is with he or she, and are with they.", True),
        ("Chinese textbook", False),
        ("Bilingual child development", False),
        ("Project evaluation", False),
    ]:
        source = ChosenSource("Learn English", "Publisher", "https://a.example", "CC BY 4.0", text)
        assert asyncio.run(policy.supports("hoc tieng anh", source)) is expected


def test_agent_rejects_licensed_but_irrelevant_pages_before_selecting_sources() -> None:
    allowlist = Allowlist(publishers=[Publisher(name="A", domains=["a.example"])])
    models = RelevanceModels()
    events = []

    async def resolve(host: str) -> list[str]:
        return ["93.184.216.34"]

    async def search(query: str, domains: Sequence[str]) -> list[SearchResult]:
        assert "beginner English" in query and "hoc tieng anh" not in query
        return [SearchResult("Learn English", "https://a.example/wrong")]

    async def event(data: dict[str, str]) -> None:
        events.append(data)

    reader = SafeReader(
        allowlist=allowlist,
        resolver=resolve,
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<p>Chinese textbook content. CC BY 4.0</p>" * 10,
            )
        ),
    )
    with pytest.raises(SourceError, match="Chưa đủ"):
        asyncio.run(
            ResearchAgent(
                search, allowlist=allowlist, reader=reader, relevance=ResearchRelevance(models)
            ).research("hoc tieng anh", event)
        )
    assert not any(e["kind"] == "select" for e in events)
    assert any("Bỏ qua" in e["text_vi"] for e in events)


def test_invalid_relevance_reply_fails_closed() -> None:
    class Invalid(RelevanceModels):
        async def generate(self, **kwargs: Any) -> ModelReply:
            return ModelReply(content={"teaches_goal": "yes"}, identity=self.item.generator)

    policy = ResearchRelevance(Invalid())
    source = ChosenSource("Title", "Publisher", "https://a.example", "CC BY 4.0", "Text")
    with pytest.raises(SourceError):
        asyncio.run(policy.supports("English", source))


def test_positive_source_claim_without_real_teaching_quote_is_rejected() -> None:
    class Fabricated(RelevanceModels):
        async def generate(self, **kwargs: Any) -> ModelReply:
            return ModelReply(
                content={
                    "teaches_goal": True,
                    "reason_vi": "Untrusted model claim",
                    "teaching_quote": "This teaching quotation does not exist in the actual page.",
                },
                identity=self.item.generator,
            )

    source = ChosenSource(
        "English course",
        "Publisher",
        "https://a.example",
        "CC BY 4.0",
        "This is only a list of links and course objectives.",
    )
    assert not asyncio.run(ResearchRelevance(Fabricated()).supports("English", source))


def test_ranking_cannot_introduce_urls_or_duplicate_candidates() -> None:
    class Ranked(RelevanceModels):
        async def generate(self, **kwargs: Any) -> ModelReply:
            return ModelReply(
                content={
                    "urls": [
                        "https://evil.example/fabricated",
                        "https://a.example/lesson",
                        "https://a.example/lesson",
                    ]
                },
                identity=self.item.generator,
            )

    candidates = [SearchResult("Lesson", "https://a.example/lesson", "Actual snippet")]
    assert asyncio.run(ResearchRelevance(Ranked()).rank("English", candidates)) == candidates


def test_query_variants_share_the_existing_search_budget() -> None:
    class Plans(RelevanceModels):
        async def generate(self, **kwargs: Any) -> ModelReply:
            return ModelReply(
                content={
                    "query": "English sentences",
                    "alternate_query": "English grammar",
                    "scope_vi": "Beginner",
                },
                identity=self.item.generator,
            )

    calls = []

    async def search(query: str, domains: Sequence[str]) -> list[SearchResult]:
        calls.append((query, domains[0]))
        return []

    async def event(data: dict[str, str]) -> None:
        pass

    allowed = Allowlist(
        publishers=[Publisher(name=str(n), domains=[f"p{n}.example"]) for n in range(5)]
    )
    with pytest.raises(SourceError):
        asyncio.run(
            ResearchAgent(
                search, allowlist=allowed, max_searches=3, relevance=ResearchRelevance(Plans())
            ).research("goal", event)
        )
    assert calls == [
        ("English sentences", "p0.example"),
        ("English grammar", "p0.example"),
        ("English sentences", "p1.example"),
    ]
