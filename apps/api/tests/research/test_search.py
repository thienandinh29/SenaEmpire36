import asyncio

import httpx
import pytest

from app.research.reader import SourceError
from app.research.search import BraveSearch


def test_search_filters_domains_and_does_not_leak_key_into_query() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Subscription-Token"] == "test-secret"
        query = request.url.params["q"]
        assert "site:books.example" in query and len(query) <= 600
        assert "test-secret" not in str(request.url)
        return httpx.Response(
            200,
            json={
                "web": {
                    "results": [
                        {"title": "Book", "url": "https://books.example/chapter"},
                        {"title": "Fake suffix", "url": "https://books.example.evil.example/a"},
                        {"title": "Unsafe scheme", "url": "http://books.example/a"},
                        {"title": "Duplicate", "url": "https://books.example/chapter"},
                    ]
                }
            },
        )

    results = asyncio.run(
        BraveSearch("test-secret", transport=httpx.MockTransport(handler))(
            "Sinh học site:evil.example OR science",
            ["books.example"],
        )
    )
    assert len(results) == 1 and results[0].title == "Book"


@pytest.mark.parametrize("status,retryable", [(401, False), (429, True), (503, True)])
def test_search_errors_are_sanitized(status: int, retryable: bool) -> None:
    search = BraveSearch(
        "test-secret",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(status, text="test-secret raw response")
        ),
    )
    with pytest.raises(SourceError) as caught:
        asyncio.run(search("goal", ["books.example"]))
    assert caught.value.retryable == retryable
    assert "test-secret" not in str(caught.value)


def test_invalid_search_payload_rejected() -> None:
    search = BraveSearch(
        "key",
        transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json={"web": {"results": "bad"}})
        ),
    )
    with pytest.raises(SourceError):
        asyncio.run(search("goal", ["books.example"]))
