"""Resumable, bounded same-book HTML acquisition; indexing remains P1/P2's job."""

import asyncio
import hashlib
import json
from collections import deque
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit

import yaml  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

from app.research.agent import canonical_url, detect_license, normalized_path
from app.research.reader import Download, SafeReader, SourceError, html_text


class Book(BaseModel):
    model_config = ConfigDict(extra="forbid")
    slug: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    title: str
    publisher: str
    start_url: str
    license_url: str
    page_prefix: str
    max_pages: int = Field(default=500, ge=1, le=1000)


class Manifest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    books: list[Book]


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            for name, value in attrs:
                if name == "href" and value:
                    self.links.append(value)


def load_manifest(path: Path) -> Manifest:
    return Manifest.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")))


def within_book(url: str, prefix: str) -> bool:
    actual, expected = urlsplit(url), urlsplit(prefix)
    path = normalized_path(actual.path).rstrip("/")
    root = normalized_path(expected.path).rstrip("/")
    return (
        actual.scheme == expected.scheme
        and actual.netloc.lower() == expected.netloc.lower()
        and (path == root or path.startswith(root + "/"))
        and not actual.query
    )


def export_library(manifest: Manifest, root: Path) -> list[dict[str, object]]:
    """Recheck local pages and export only hash/license/scope-valid records for P1 ingestion."""
    reports: list[dict[str, object]] = []
    for book in manifest.books:
        directory = root / book.slug
        if not directory.exists():
            reports.append(
                {"book": book.slug, "accepted_pages": 0, "rejected": [], "missing": True}
            )
            continue
        records: list[dict[str, str]] = []
        seen: set[str] = set()
        rejected: list[dict[str, str]] = []
        paths = sorted(path for path in directory.glob("*.json") if path.name != "report.json")
        # Bound concurrent disk reads; map preserves stable output order for reproducibility.
        with ThreadPoolExecutor(max_workers=8) as pool:
            for record, rejection in pool.map(partial(_audit_page, book=book), paths):
                if rejection is not None:
                    rejected.append(rejection)
                if record is not None and record["url"] not in seen:
                    seen.add(record["url"])
                    records.append(record)
        temporary = directory / "index.jsonl.tmp"
        with temporary.open("w", encoding="utf-8") as output:
            for record in records:
                output.write(json.dumps(record, ensure_ascii=False) + "\n")
        temporary.replace(directory / "index.jsonl")
        reports.append(
            {
                "book": book.slug,
                "accepted_pages": len(records),
                "rejected": rejected,
                "missing": False,
            }
        )
    return reports


def _audit_page(path: Path, *, book: Book) -> tuple[dict[str, str] | None, dict[str, str] | None]:
    try:
        metadata = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(metadata, dict):
            raise ValueError("Invalid metadata object")
        uri, checksum = metadata.get("source_uri"), metadata.get("sha256")
        if not isinstance(uri, str) or not isinstance(checksum, str):
            raise ValueError("Missing provenance")
        if not within_book(uri, book.page_prefix):
            raise ValueError("Source URL outside book scope")
        raw = path.with_suffix(".html").read_bytes()
        if hashlib.sha256(raw).hexdigest() != checksum:
            raise ValueError("Source hash mismatch")
        text = html_text(raw)
        license_name = detect_license(text)
        return {
            "url": canonical_url(uri),
            "source_uri": uri,
            "title": book.title,
            "publisher": book.publisher,
            "license": license_name,
            "license_url": book.license_url,
            "sha256": checksum,
            "text": text,
        }, None
    except (ValueError, OSError, SourceError) as exc:
        return None, {"file": path.name, "reason": str(exc)}


async def _fetch(reader: SafeReader, url: str) -> Download:
    for attempt in range(3):
        try:
            return await reader.fetch(url)
        except SourceError as exc:
            if not exc.retryable or attempt == 2:
                raise
            await asyncio.sleep(0.2 * 2**attempt)
    raise AssertionError("Unreachable retry state")


async def download_book(book: Book, root: Path, reader: SafeReader) -> dict[str, object]:
    """Store raw HTML and provenance JSON per page, plus a completeness/failure report."""
    if reader.allowlist is None:
        raise ValueError("Library downloads require an allowlist")
    if reader.allowlist.publisher(book.start_url).name != book.publisher:
        raise ValueError("Manifest publisher does not match the allowlist")
    if reader.allowlist.publisher(book.license_url).name != book.publisher:
        raise ValueError("License page must belong to the same publisher")
    if not within_book(book.start_url, book.page_prefix):
        raise ValueError("Start URL is outside the book prefix")
    license_page = await _fetch(reader, book.license_url)
    if reader.allowlist.publisher(license_page.url).name != book.publisher:
        raise ValueError("License page redirected to a different publisher")
    license_name = detect_license(html_text(license_page.body))
    directory = root / book.slug
    directory.mkdir(parents=True, exist_ok=True)
    queue = deque([canonical_url(book.start_url)])
    seen: set[str] = set()
    failures: list[dict[str, str]] = []
    downloaded = cached = 0
    truncated = False
    while queue and len(seen) < book.max_pages:
        url = queue.popleft()
        if url in seen:
            continue
        seen.add(url)
        key = hashlib.sha256(url.encode()).hexdigest()
        html_path, metadata_path = directory / f"{key}.html", directory / f"{key}.json"
        try:
            cache_valid = False
            if html_path.exists() and metadata_path.exists():
                raw = html_path.read_bytes()
                try:
                    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
                    cache_valid = (
                        metadata.get("sha256") == hashlib.sha256(raw).hexdigest()
                        and metadata.get("url") == url
                    )
                except (ValueError, AttributeError):
                    cache_valid = False
            if cache_valid:
                cached += 1
            else:
                response = await _fetch(reader, url)
                if not within_book(response.url, book.page_prefix):
                    raise SourceError("Trang chuyển hướng ra ngoài giáo trình.")
                if response.content_type.partition(";")[0] not in {
                    "text/html",
                    "application/xhtml+xml",
                }:
                    raise SourceError("Trang giáo trình không phải HTML.")
                raw = response.body
                text = html_text(raw)
                page_license = detect_license(text)
                if sum(c.isalnum() for c in text) < 40:
                    raise SourceError("Trang không có đủ văn bản để lập chỉ mục.")
                metadata = {
                    "url": url,
                    "source_uri": response.url,
                    "title": book.title,
                    "publisher": book.publisher,
                    "license": page_license,
                    "license_url": license_page.url,
                    "text": text,
                    "sha256": hashlib.sha256(raw).hexdigest(),
                }
                html_path.write_bytes(raw)
                metadata_path.write_text(json.dumps(metadata, ensure_ascii=False), encoding="utf-8")
                downloaded += 1
            parser = _Links()
            parser.feed(raw.decode("utf-8", errors="replace"))
            for link in parser.links:
                next_url = canonical_url(urljoin(url, link))
                if (
                    within_book(next_url, book.page_prefix)
                    and next_url not in seen
                    and next_url not in queue
                ):
                    if len(queue) < book.max_pages:
                        queue.append(next_url)
                    else:
                        truncated = True
        except SourceError as exc:
            failures.append({"url": url, "error_vi": str(exc)})
        await asyncio.sleep(0)  # Let worker cancellation/deadlines interrupt between cached pages.
    report: dict[str, object] = {
        "book": book.slug,
        "license": license_name,
        "downloaded": downloaded,
        "cached": cached,
        "failures": failures,
        "discovery_exhausted": not queue and not truncated,
        "complete": not queue and not truncated and not failures,
    }
    (directory / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return report
