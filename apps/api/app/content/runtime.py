"""Bind P4 adapters into P2's existing app; no duplicate routes or application framework."""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.content.backends import LearningBackend, TopicsBackend, TutorBackend
from app.content.gateway import Gateway, P3Gateway
from app.content.learning import GraphConfirmation
from app.content.repository import Repository
from app.main import create_app as platform_app
from app.main import create_content_app


def create_app(
    settings: Settings | None = None,
    *,
    repository: Repository | None = None,
    gateway: Gateway | None = None,
    confirmation: GraphConfirmation | None = None,
) -> FastAPI:
    """Legacy P4 entry point using the same repository settings as API and worker."""
    settings = settings or get_settings()
    if repository is None and gateway is None and confirmation is None:
        # Normal launches use the complete P1-P5 composition, including durable
        # confirmations, learner credentials and platform upload storage.
        return create_content_app(settings)
    app: FastAPI
    store = repository or Repository(lambda: app.state.pool)
    models = gateway or P3Gateway()
    app = platform_app(
        settings,
        learning_backend=LearningBackend(store, confirmation, models),
        topics_backend=TopicsBackend(store),
        tutor_backend=TutorBackend(
            store, models, confirmation, demo_uploads_enabled=settings.demo_uploads_enabled
        ),
    )
    platform_lifespan = app.router.lifespan_context

    @asynccontextmanager
    async def lifespan(current: FastAPI) -> AsyncIterator[None]:
        async with platform_lifespan(current):
            await asyncio.to_thread(store.require_schema)
            yield

    app.router.lifespan_context = lifespan
    app.state.p4_repository = store
    return app
