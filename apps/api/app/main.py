from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from pydantic import BaseModel

from app.config import Settings, get_settings
from app.db import create_pool, ping


class Health(BaseModel):
    status: str
    db: str


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.pool = create_pool(settings.database_url)
        try:
            yield
        finally:
            app.state.pool.close()

    app = FastAPI(title="NodeTrail API", lifespan=lifespan)

    @app.get("/health")
    def health(request: Request) -> Health:
        db_ok = ping(request.app.state.pool)
        return Health(status="ok", db="ok" if db_ok else "down")

    return app


app = create_app()
