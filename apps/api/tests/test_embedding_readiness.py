import asyncio

import httpx
import pytest
from fastapi import HTTPException

from app.config import Settings
from app.services.topic_readiness import embedding_status, require_embedding_ready


def test_http_rejects_job_before_enqueue_when_embedding_is_loading(database_url, monkeypatch):
    from fastapi.testclient import TestClient

    from app.main import create_app

    class NeverEnqueue:
        async def enqueue(self, request):
            pytest.fail("Job must not be accepted while embedding is loading")

    async def loading(settings):
        return "loading"

    monkeypatch.setattr("app.services.topic_readiness.embedding_status", loading)
    app = create_app(
        Settings(_env_file=None, database_url=database_url, api_key="test"),
        topics_backend=NeverEnqueue(),
    )
    app.state.embedding_required = True
    with TestClient(app, headers={"X-API-Key": "test"}) as client:
        r = client.post("/topics", json={"goal_vi": "Real input", "mode": "quick", "tier": "free"})
        assert r.status_code == 503
        assert r.json()["detail"]["code"] == "embedding_loading"


@pytest.mark.parametrize(
    "health,model,expected",
    [
        (503, "BAAI/bge-m3", "loading"),
        (500, "BAAI/bge-m3", "error"),
        (200, "another-model", "model_mismatch"),
        (200, "BAAI/bge-m3", "ready"),
    ],
)
def test_embedding_readiness_classification(monkeypatch, health, model, expected):
    client_type = httpx.AsyncClient

    def respond(request):
        return httpx.Response(
            health if request.url.path == "/health" else 200, json={"model_id": model}
        )

    monkeypatch.setattr(
        "app.services.topic_readiness.httpx.AsyncClient",
        lambda **kwargs: client_type(**kwargs, transport=httpx.MockTransport(respond)),
    )
    settings = Settings(_env_file=None)
    assert asyncio.run(embedding_status(settings)) == expected
    if expected != "ready":
        with pytest.raises(HTTPException) as caught:
            asyncio.run(require_embedding_ready(settings))
        assert caught.value.status_code == 503
        assert caught.value.detail["code"] == "embedding_" + expected
