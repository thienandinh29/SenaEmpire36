from collections.abc import Iterator
from io import BytesIO

import pytest
from pypdf import PdfWriter

from tests.api.conftest import Harness
from tests.uploads.test_reader import docx


def test_topic_submission_only_enqueues(harness: Harness) -> None:
    response = harness.client.post(
        "/topics",
        json={
            "goal_vi": "Học Python",
            "mode": "quick",
            "tier": "free",
        },
    )
    assert response.status_code == 200
    assert response.json() == {"topic_id": "topic-1", "cached": False}
    assert len(harness.backend.jobs) == 1
    assert harness.backend.jobs[0].goal_vi == "Học Python"


@pytest.mark.parametrize(
    "body",
    [
        {"mode": "quick", "tier": "free"},
        {"goal_vi": "   ", "mode": "quick", "tier": "free"},
        {"goal_vi": "Python", "mode": "deep", "tier": "free"},
        {"goal_vi": "Python", "mode": "quick", "tier": "unknown"},
    ],
)
def test_invalid_topic_never_creates_job(harness: Harness, body: dict[str, str]) -> None:
    assert harness.client.post("/topics", json=body).status_code == 422
    assert not harness.backend.jobs


def test_upload_id_can_seed_a_topic(harness: Harness) -> None:
    response = harness.client.post(
        "/topics",
        json={
            "upload_id": "upload-1",
            "mode": "deep",
            "tier": "pro",
        },
    )
    assert response.status_code == 200
    assert harness.backend.jobs[0].upload_id == "upload-1"


def test_json_link_upload(harness: Harness) -> None:
    response = harness.client.post("/uploads", json={"url": "https://books.example/chapter"})
    assert response.status_code == 200
    assert response.json() == {"upload_id": "upload-1", "pages": 1, "text_ok": True}
    document, body, filename = harness.backend.uploads[0]
    assert document.source_uri == "https://books.example/chapter"
    assert body is None and filename is None


def test_multipart_docx_invokes_real_extractor(harness: Harness) -> None:
    data = docx(
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>Kiến thức nền tảng giúp người học hiểu và vận dụng bài học."
        "</w:t></w:r></w:p></w:body></w:document>"
    )
    response = harness.client.post(
        "/uploads",
        files={
            "file": (
                "../../syllabus.docx",
                data,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert response.status_code == 200 and response.json()["text_ok"]
    document, body, filename = harness.backend.uploads[0]
    assert filename == "syllabus.docx" and body == data
    assert "Kiến thức" in document.pages[0].text
    assert document.source_uri == ""  # Persistence adapter assigns the actual Storage URI.


def test_unreadable_pdf_is_reported_without_enqueuing(harness: Harness) -> None:
    buffer = BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.write(buffer)
    response = harness.client.post("/uploads", files={"file": ("scan.pdf", buffer.getvalue())})
    assert response.status_code == 200
    assert response.json()["text_ok"] is False and response.json()["pages"] == 1
    assert not harness.backend.jobs


@pytest.mark.parametrize("filename,body", [("bad.pdf", b"broken"), ("script.exe", b"MZ")])
def test_invalid_file_never_persisted(harness: Harness, filename: str, body: bytes) -> None:
    response = harness.client.post("/uploads", files={"file": (filename, body)})
    assert response.status_code == 422
    assert not harness.backend.uploads


def test_multiple_files_rejected(harness: Harness) -> None:
    response = harness.client.post(
        "/uploads",
        files=[
            ("file", ("one.pdf", b"one")),
            ("file", ("two.pdf", b"two")),
        ],
    )
    assert response.status_code == 413
    assert not harness.backend.uploads


def test_oversized_stream_without_content_length(harness: Harness) -> None:
    def chunks() -> Iterator[bytes]:
        yield b'{"url":"'
        yield b"x" * 20_000

    response = harness.client.post(
        "/uploads", content=chunks(), headers={"content-type": "application/json"}
    )
    assert response.status_code == 413
    assert not harness.backend.uploads


def test_invalid_json_and_unsupported_media(harness: Harness) -> None:
    assert (
        harness.client.post(
            "/uploads", content=b"{", headers={"content-type": "application/json"}
        ).status_code
        == 422
    )
    assert (
        harness.client.post(
            "/uploads", content=b"hello", headers={"content-type": "text/plain"}
        ).status_code
        == 415
    )
