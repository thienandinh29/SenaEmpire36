"""Bounded PDF/DOCX/HTML text extraction with page provenance; no OCR."""

import asyncio
import re
import unicodedata
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from app.research.reader import SafeReader, SourceError, html_content, html_text

MAX_BYTES = 20_000_000
MAX_PAGES = 200
MAX_TEXT = 2_000_000
W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


@dataclass(frozen=True)
class Page:
    number: int
    text: str


@dataclass(frozen=True)
class Document:
    source_uri: str
    pages: tuple[Page, ...]
    text_ok: bool
    media_type: str = "text/plain"
    license_text: str = ""


def _document(uri: str, pages: list[Page], media_type: str = "text/plain") -> Document:
    normalized = tuple(Page(p.number, unicodedata.normalize("NFC", p.text)) for p in pages)
    text = "\n".join(p.text for p in normalized)
    if len(text) > MAX_TEXT:
        raise SourceError("Văn bản vượt giới hạn xử lý.")
    useful = sum(char.isalnum() for char in text)
    text_ok = useful >= 40 and text.count("\ufffd") <= max(1, len(text) // 100)
    return Document(uri, normalized, text_ok, media_type)


def read_file(filename: str, body: bytes, source_uri: str, *, query: str | None = None) -> Document:
    if not body or len(body) > MAX_BYTES:
        raise SourceError("Tệp rỗng hoặc vượt giới hạn 20 MB.")
    suffix = PurePosixPath(filename).suffix.lower()
    try:
        if suffix == ".pdf":
            if not body.startswith(b"%PDF-"):
                raise SourceError("Nội dung tệp không phải PDF.")
            reader = PdfReader(BytesIO(body))
            if reader.is_encrypted:
                raise SourceError("PDF được mã hóa; vui lòng dùng tệp không có mật khẩu.")
            selected = list(range(len(reader.pages)))
            extracted: dict[int, str] = {}
            if len(selected) > MAX_PAGES:
                if not query:
                    raise SourceError(
                        "Tài liệu dài hơn 200 trang; cần mục tiêu để chọn chương/trang phù hợp."
                    )
                terms = {w for w in re.findall(r"\w+", query.casefold()) if len(w) > 3}
                if not terms:
                    raise SourceError("Cần mục tiêu cụ thể để chọn trang trong tài liệu dài.")
                scores = []
                for i in range(min(len(reader.pages), 2000)):
                    text = reader.pages[i].extract_text() or ""
                    score = sum(min(text.casefold().count(w), 8) for w in terms)
                    if score:
                        scores.append((score, i, text))
                best = sorted(scores, reverse=True)[:8]
                if not best:
                    raise SourceError(
                        "Chưa tìm thấy chương phù hợp trong tài liệu dài; "
                        "hãy chọn tài liệu cụ thể hơn."
                    )
                selected = sorted(
                    set(range(min(6, len(reader.pages))))
                    | {
                        p
                        for _, i, _ in best
                        for p in range(max(0, i - 1), min(len(reader.pages), i + 2))
                    }
                )
                extracted = {i: text for _, i, text in best}
            pages: list[Page] = []
            size = 0
            for index in selected:
                text = extracted.get(index)
                if text is None:
                    text = reader.pages[index].extract_text() or ""
                size += len(text)
                if size > MAX_TEXT:
                    raise SourceError("Văn bản vượt giới hạn xử lý.")
                pages.append(Page(index + 1, text))
            return _document(source_uri, pages, "application/pdf")
        if suffix == ".docx":
            with ZipFile(BytesIO(body)) as archive:
                entries = archive.infolist()
                if (
                    len(entries) > 2000
                    or sum(e.file_size for e in entries) > 40_000_000
                    or any(e.flag_bits & 1 for e in entries)
                ):
                    raise SourceError("DOCX vượt giới hạn giải nén hoặc được mã hóa.")
                xml = archive.read("word/document.xml")
            if b"<!DOCTYPE" in xml.upper() or b"<!ENTITY" in xml.upper():
                raise SourceError("Cấu trúc DOCX không được hỗ trợ.")
            root = ElementTree.fromstring(xml)
            # DOCX pagination depends on Word layout; only explicit page breaks are reliable.
            segments: list[list[str]] = [[]]
            for element in root.iter():
                if element.tag == W + "t" and element.text:
                    segments[-1].append(element.text)
                elif element.tag in {W + "tab", W + "br"}:
                    if element.get(W + "type") == "page":
                        segments.append([])
                    else:
                        segments[-1].append("\n")
                elif element.tag == W + "p":
                    segments[-1].append("\n")
                if len(segments) > MAX_PAGES:
                    raise SourceError("Tài liệu vượt giới hạn 200 trang.")
            return _document(
                source_uri,
                [Page(index, "".join(parts)) for index, parts in enumerate(segments, 1)],
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
    except (PdfReadError, BadZipFile, KeyError, ElementTree.ParseError, ValueError):
        raise SourceError("Tệp bị hỏng hoặc không thể đọc văn bản.") from None
    raise SourceError("Chỉ hỗ trợ tệp PDF hoặc DOCX.")


async def read_link(
    url: str, reader: SafeReader | None = None, *, query: str | None = None
) -> Document:
    download = await (reader or SafeReader()).fetch(url)
    media = download.content_type.partition(";")[0].strip().lower()
    if media == "application/pdf" or download.body.startswith(b"%PDF-"):
        return await asyncio.to_thread(
            read_file, "upload.pdf", download.body, download.url, query=query
        )
    if media == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
        return await asyncio.to_thread(read_file, "upload.docx", download.body, download.url)
    if media not in {"text/html", "application/xhtml+xml", "text/plain"}:
        raise SourceError("Đường dẫn không trả về tài liệu được hỗ trợ.")
    text = (
        download.body.decode("utf-8-sig", errors="replace")
        if media == "text/plain"
        else html_content(download.body)
    )
    document = _document(download.url, [Page(1, text)], media)
    return Document(
        document.source_uri,
        document.pages,
        document.text_ok,
        media,
        html_text(download.body) if media != "text/plain" else text,
    )
