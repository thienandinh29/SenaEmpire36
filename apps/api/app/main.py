import asyncio
import json
import logging
import secrets
import time
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from starlette.responses import Response

from app.config import Settings, get_settings
from app.db import create_pool, ping
from app.jobs.queue import snapshot
from app.observability import configure_logging

logger = logging.getLogger(__name__)
HEARTBEAT_SECONDS = 15


class LearnerInput(BaseModel):
    display_name: str = Field(min_length=1, max_length=200, pattern=r"\S")


class Health(BaseModel):
    status: str
    db: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    configure_logging()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.pool = create_pool(settings.database_url)
        try:
            yield
        finally:
            app.state.pool.close()

    app = FastAPI(title="NodeTrail API", lifespan=lifespan)

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        request_id = str(uuid4())
        started = time.monotonic()
        response: Response
        if (
            settings.api_key
            and request.url.path != "/health"
            and not secrets.compare_digest(
                request.headers.get("x-api-key", "").encode(), settings.api_key.encode()
            )
        ):
            response = JSONResponse({"detail": "API key không hợp lệ"}, status_code=401)
        else:
            try:
                response = await call_next(request)
            except Exception:
                logger.exception("request failed", extra={"request_id": request_id})
                response = JSONResponse(
                    {"detail": "Không thể xử lý yêu cầu", "request_id": request_id}, status_code=503
                )
        response.headers["X-Request-ID"] = request_id
        logger.info(
            "request completed",
            extra={
                "request_id": request_id,
                "topic_id": request.path_params.get("topic_id"),
                "tier": getattr(request.state, "tier", None),
                "status": response.status_code,
                "latency_ms": round((time.monotonic() - started) * 1000),
            },
        )
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=[origin.strip() for origin in settings.cors_origins.split(",")],
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["X-API-Key", "Content-Type", "Last-Event-ID"],
        expose_headers=["X-Request-ID", "X-Data-Fixture"],
    )

    @app.post("/learners")
    def create_learner(body: LearnerInput, request: Request) -> dict[str, UUID]:
        with request.app.state.pool.connection() as conn:
            row = conn.execute(
                "insert into learners(display_name) values (%s) returning id",
                (body.display_name.strip(),),
            ).fetchone()
        assert row is not None
        return {"learner_id": row[0]}

    @app.get("/topics/cached")
    def cached_topics(request: Request) -> dict[str, list[dict[str, str]]]:
        with request.app.state.pool.connection() as conn:
            rows = conn.execute(
                "select distinct s.slug,s.name_vi from topic_jobs j "
                "join subjects s on s.slug=j.subject_slug "
                "where j.status='ready' and not j.fixture and j.graph_ready and j.items_ready"
            ).fetchall()
        return {"topics": [{"subject_slug": r[0], "name_vi": r[1]} for r in rows]}

    def topic_state(topic_id: UUID, request: Request) -> tuple[dict[str, Any], bool]:
        with request.app.state.pool.connection() as conn:
            state = snapshot(conn, topic_id)
            metadata = conn.execute(
                "select fixture,tier from topic_jobs where id=%s", (topic_id,)
            ).fetchone()
        if state is None or metadata is None:
            raise HTTPException(404, "Không tìm thấy chủ đề")
        request.state.tier = metadata[1]
        return state, metadata[0]

    @app.get("/topics/{topic_id}")
    def get_topic(topic_id: UUID, request: Request) -> JSONResponse:
        state, fixture = topic_state(topic_id, request)
        return JSONResponse(state, headers={"X-Data-Fixture": str(fixture).lower()})

    @app.get("/topics/{topic_id}/events")
    async def topic_events(topic_id: UUID, request: Request) -> StreamingResponse:
        initial, fixture = await asyncio.to_thread(topic_state, topic_id, request)

        async def stream() -> AsyncIterator[str]:
            state = initial
            previous = ""
            heartbeat = time.monotonic()
            while not await request.is_disconnected():
                data = json.dumps(state, ensure_ascii=False)
                if data != previous:
                    yield f"event: message\ndata: {data}\n\n"
                    previous = data
                if state["status"] in ("ready", "failed"):
                    return
                if time.monotonic() - heartbeat >= HEARTBEAT_SECONDS:
                    yield "event: heartbeat\ndata: {}\n\n"
                    heartbeat = time.monotonic()
                await asyncio.sleep(1)
                state, _ = await asyncio.to_thread(topic_state, topic_id, request)

        return StreamingResponse(
            stream(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "X-Accel-Buffering": "no",
                "X-Data-Fixture": str(fixture).lower(),
            },
        )

    @app.get("/health")
    def health(request: Request) -> Health:
        db_ok = ping(request.app.state.pool)
        return Health(status="ok", db="ok" if db_ok else "down")

    return app


app = create_app()
