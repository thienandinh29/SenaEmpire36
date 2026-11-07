import pytest

from tests.api.conftest import Harness


@pytest.mark.parametrize("path", ["/ask", "/tutor/hint"])
def test_cited_supported_content_has_only_public_fields(harness: Harness, path: str) -> None:
    body = (
        {"question": "Quang hợp là gì?", "subject": "biology", "tier": "free"}
        if path == "/ask"
        else {"learner_id": "u1", "item_id": "q1", "level": 1, "tier": "pro"}
    )
    response = harness.client.post(path, json=body)
    assert response.status_code == 200
    key = "answer_vi" if path == "/ask" else "hint_vi"
    assert set(response.json()) == {key, "citations"}
    assert response.json()["citations"][0]["url"].startswith("https://")


@pytest.mark.parametrize("path", ["/ask", "/tutor/hint"])
@pytest.mark.parametrize("failure", ["unsupported", "uncited", "blank"])
def test_unverified_content_is_withheld(harness: Harness, path: str, failure: str) -> None:
    if failure == "unsupported":
        harness.backend.text.supported = False
    elif failure == "uncited":
        harness.backend.text.citations = []
    else:
        harness.backend.text.text_vi = "   "
    body = (
        {"question": "Quang hợp?", "subject": "biology", "tier": "free"}
        if path == "/ask"
        else {"learner_id": "u1", "item_id": "q1", "level": 1, "tier": "pro"}
    )
    response = harness.client.post(path, json=body)
    assert response.status_code == 503
    assert "citations" not in response.json()
