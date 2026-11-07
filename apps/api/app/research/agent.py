"""Research runner; search backend injection keeps vendor selection with the team."""

import asyncio
import math
import posixpath
import re
from collections.abc import Awaitable, Callable, Sequence
from dataclasses import dataclass
from time import monotonic
from typing import TYPE_CHECKING
from urllib.parse import quote, unquote, urlsplit, urlunsplit

if TYPE_CHECKING:
    from app.research.relevance import ResearchRelevance

from app.research.reader import Allowlist, SafeReader, SourceError, load_allowlist
from app.uploads.reader import read_link


@dataclass(frozen=True)
class SearchResult:
    title: str
    url: str
    snippet: str = ""


@dataclass(frozen=True)
class ChosenSource:
    title: str
    publisher: str
    url: str
    license: str
    text: str


Search = Callable[[str, Sequence[str]], Awaitable[Sequence[SearchResult]]]
OnEvent = Callable[[dict[str, str]], Awaitable[None]]


def detect_license(text: str) -> str:
    """Accept explicit CC grants found in the document, never search-result metadata."""
    normalized = text.casefold()
    if re.search(r"shared under (?:a )?not declared license", normalized):
        raise SourceError("Chưa có giấy phép được công bố cho trang tài liệu này.")
    if re.search(
        r"may not.{0,180}(?:ingested into large language models|training of large language models)",
        " ".join(normalized.split()),
    ):
        raise SourceError("Nguồn yêu cầu chấp thuận riêng trước khi dùng với mô hình AI.")
    if re.search(
        r"\bby(?:[-\s]+nc)?[-\s]+nd\b|creativecommons.org/licenses/by[^\s]*nd", normalized
    ):
        raise SourceError("Không sử dụng tài liệu có giấy phép ND.")
    for code in ("by-nc-sa", "by-nc", "by-sa", "by"):
        found = re.search(
            rf"(?:creativecommons\.org/licenses/{code}/|\bcc[ -]+{code}[ /]+)([1-4]\.0)",
            normalized,
        )
        if found:
            return f"CC {code.upper()} {found[1]}"
    for name, code in (
        ("attribution-noncommercial-sharealike", "BY-NC-SA"),
        ("attribution-noncommercial", "BY-NC"),
        ("attribution-sharealike", "BY-SA"),
        ("attribution", "BY"),
    ):
        found = re.search(rf"creative commons {name}\s+([1-4]\.0)\b", normalized)
        if found:
            return f"CC {code} {found[1]}"
    if "creativecommons.org/publicdomain/zero/1.0" in normalized or "cc0 1.0" in normalized:
        return "CC0 1.0"
    raise SourceError("Chưa xác định được giấy phép mở của tài liệu.")


def canonical_url(url: str) -> str:
    parsed = urlsplit(url)
    host = parsed.netloc.lower()
    if host.endswith(":443"):
        host = host[:-4]
    return urlunsplit(
        (
            parsed.scheme,
            host,
            quote(normalized_path(parsed.path).rstrip("/"), safe="/:@"),
            parsed.query,
            "",
        )
    )


def normalized_path(path: str) -> str:
    for _ in range(3):
        decoded = unquote(path)
        if decoded == path:
            break
        path = decoded
    return posixpath.normpath(path)


class ResearchAgent:
    def __init__(
        self,
        search: Search,
        *,
        allowlist: Allowlist | None = None,
        reader: SafeReader | None = None,
        max_searches: int = 15,
        max_reads: int = 12,
        deadline_seconds: float = 480,
        relevance: "ResearchRelevance | None" = None,
    ) -> None:
        if not (1 <= max_searches <= 15 and 1 <= max_reads <= 12 and 0 < deadline_seconds <= 480):
            raise ValueError("Research limits exceed the contract")
        self.allowlist = allowlist or load_allowlist()
        if reader is not None and reader.allowlist != self.allowlist:
            raise ValueError("Research reader must enforce the same allowlist")
        self.reader = reader or SafeReader(allowlist=self.allowlist)
        self.search = search
        self.relevance = relevance
        self.max_searches, self.max_reads, self.deadline = max_searches, max_reads, deadline_seconds

    async def research(self, goal: str, on_event: OnEvent) -> list[ChosenSource]:
        if not goal.strip() or len(goal) > 2000:
            raise SourceError("Mục tiêu học tập rỗng hoặc quá dài.")
        publisher_count = sum(not p.fallback_only for p in self.allowlist.publishers)
        per_publisher_reads = max(1, math.ceil(self.max_reads / max(1, publisher_count)))
        seen: set[str] = set()
        selected_urls: set[str] = set()
        sources: list[ChosenSource] = []
        publishers: set[str] = set()
        searches = reads = 0
        started = monotonic()

        async def event(kind: str, text: str, url: str = "") -> None:
            await on_event(
                {
                    "kind": kind,
                    "text_vi": text,
                    "url": url,
                    "elapsed_seconds": f"{monotonic() - started:.1f}",
                }
            )

        try:
            async with asyncio.timeout(self.deadline):
                search_goal = goal.strip()
                alternate_query = ""
                if self.relevance is not None:
                    plan = await self.relevance.plan(goal)
                    search_goal = plan.query
                    alternate_query = plan.alternate_query
                    await event("search", "Phạm vi tìm tài liệu: " + plan.scope_vi)
                for publisher in self.allowlist.publishers:
                    if (
                        publisher.fallback_only
                        or searches >= self.max_searches
                        or reads >= self.max_reads
                    ):
                        continue
                    searches += 1
                    # Adapters receive the domain scope separately. Do not turn site:
                    # operators into stray query words when sanitizing model queries.
                    query = (
                        search_goal
                        if self.relevance
                        else (f"{search_goal} textbook site:{publisher.domains[0]}")
                    )
                    await event("search", f"Đang tìm giáo trình tại {publisher.name}…")
                    try:
                        results = await self.search(query, publisher.domains)
                        if self.relevance:
                            if (
                                alternate_query
                                and alternate_query != query
                                and searches < self.max_searches
                            ):
                                searches += 1
                                alternatives = await self.search(alternate_query, publisher.domains)
                                results = list(results[:6]) + list(alternatives[:6])
                            results = await self.relevance.rank(goal, results)
                            # Prefer individual HTML lessons over whole-book downloads.
                            results = sorted(
                                results,
                                key=lambda r: (
                                    urlsplit(r.url).path.lower().endswith(".pdf")
                                    or "/open/download" in r.url
                                ),
                            )
                    except SourceError as exc:
                        if exc.retryable:
                            continue
                        raise
                    publisher_reads = publisher_selected = 0
                    for result in results:
                        if (
                            reads >= self.max_reads
                            or publisher_reads
                            >= (
                                max(3, per_publisher_reads)
                                if self.relevance
                                else per_publisher_reads
                            )
                            or publisher_selected >= 2
                        ):
                            break
                        key = canonical_url(result.url)
                        if key in seen:
                            continue
                        seen.add(key)
                        try:
                            self.allowlist.publisher(result.url)
                        except SourceError:
                            continue
                        reads += 1
                        publisher_reads += 1
                        await event("read", f"Đang đọc {result.title}…", result.url)
                        try:
                            document = await read_link(result.url, self.reader)
                            actual = self.allowlist.publisher(document.source_uri)
                            final_url = canonical_url(document.source_uri)
                            if final_url in selected_urls:
                                continue
                            if not document.text_ok:
                                continue
                            text = "\n".join(p.text for p in document.pages)
                            license_name = detect_license(text)
                        except SourceError:
                            continue
                        candidate = ChosenSource(
                            result.title,
                            actual.name,
                            document.source_uri,
                            license_name,
                            text,
                        )
                        if self.relevance is not None and not await self.relevance.supports(
                            goal, candidate
                        ):
                            await event(
                                "read",
                                "Bỏ qua nguồn không có bài học đúng mục tiêu: " + result.title,
                                document.source_uri,
                            )
                            continue
                        sources.append(candidate)
                        selected_urls.add(final_url)
                        publisher_selected += 1
                        publishers.add(actual.name)
                        await event(
                            "select",
                            f"Đã chọn {result.title} ({license_name}).",
                            document.source_uri,
                        )
                        if len(sources) >= 3 and len(publishers) >= 2:
                            return sources
        except TimeoutError:
            raise SourceError("Nghiên cứu đã hết thời gian; hãy thử chế độ Nhanh.") from None
        raise SourceError("Chưa đủ 3 nguồn từ 2 nhà xuất bản; hãy thử chế độ Nhanh.")


async def research(goal: str, on_event: OnEvent) -> list[ChosenSource]:
    """Public entry point requires a job-local backend, configured by the worker."""
    from app.research.runtime import current_agent

    return await current_agent().research(goal, on_event)
