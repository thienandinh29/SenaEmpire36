"""Brave Web Search adapter; provider filtering plus independent local domain checks."""

import os
import re
from collections.abc import Sequence

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.research.agent import ResearchAgent, SearchResult
from app.research.reader import SourceError, validate_url


class _Result(BaseModel):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)


class _Web(BaseModel):
    results: list[_Result] = Field(default_factory=list)


class _Response(BaseModel):
    model_config = ConfigDict(extra="ignore")
    web: _Web = Field(default_factory=_Web)


class BraveSearch:
    def __init__(
        self,
        api_key: str,
        *,
        count: int = 12,
        timeout: float = 15,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        if not api_key or not 1 <= count <= 20 or timeout <= 0:
            raise ValueError("Brave API key and valid search limits are required")
        self.api_key, self.count, self.timeout = api_key, count, timeout
        self.transport = transport

    async def __call__(self, query: str, domains: Sequence[str]) -> list[SearchResult]:
        if not domains or any(not re.fullmatch(r"[a-z0-9]+(?:[.-][a-z0-9]+)*", d) for d in domains):
            raise SourceError("Danh sách miền tìm kiếm không hợp lệ.")
        # Discard operators supplied in a learner goal. Query operators come only from config.
        words = re.findall(r"[^\W_]+", query, flags=re.UNICODE)
        scope = "(" + " OR ".join("site:" + d for d in dict.fromkeys(domains)) + ")"
        budget = 600 - len(scope) - 1
        clean = " ".join(words[: max(1, 70 - 2 * len(domains))])[:budget].strip()
        if not clean or budget < 1:
            raise SourceError("Mục tiêu tìm kiếm không hợp lệ.")
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout,
                trust_env=False,
                transport=self.transport,
            ) as client:
                # No automatic retry: each call counts once toward the research search budget.
                response = await client.get(
                    "https://api.search.brave.com/res/v1/web/search",
                    headers={"X-Subscription-Token": self.api_key, "Accept": "application/json"},
                    params={
                        "q": f"{clean} {scope}",
                        "count": self.count,
                        "result_filter": "web",
                        "text_decorations": "false",
                    },
                )
                response.raise_for_status()
                parsed = _Response.model_validate_json(response.content)
        except httpx.HTTPStatusError as exc:
            status = exc.response.status_code
            raise SourceError(
                f"Dịch vụ tìm kiếm trả về lỗi HTTP {status}.",
                retryable=status == 429 or status >= 500,
            ) from None
        except (httpx.RequestError, ValidationError):
            raise SourceError("Dịch vụ tìm kiếm tạm thời không khả dụng.", retryable=True) from None
        results: list[SearchResult] = []
        seen: set[str] = set()
        for entry in parsed.web.results[: self.count]:
            try:
                host = validate_url(entry.url)
            except SourceError:
                continue
            if (
                any(host == domain or host.endswith("." + domain) for domain in domains)
                and entry.url not in seen
            ):
                results.append(SearchResult(entry.title, entry.url))
                seen.add(entry.url)
        return results


def default_agent() -> ResearchAgent:
    provider = os.environ.get("SEARCH_PROVIDER", "brave")
    if provider != "brave":
        raise SourceError("Nhà cung cấp tìm kiếm chưa được hỗ trợ.")
    key = os.environ.get("SEARCH_API_KEY", "")
    if not key:
        raise SourceError("Dịch vụ tìm kiếm chưa được cấu hình.")
    return ResearchAgent(BraveSearch(key))
