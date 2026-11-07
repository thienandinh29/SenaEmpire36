"""Isolated feature entry point: uvicorn app.school.main:create_school_app --factory."""

from fastapi import FastAPI

from app.config import Settings, get_settings
from app.content.gateway import Gateway, P3Gateway
from app.content.repository import Repository
from app.main import create_content_app
from app.school.routes import create_router
from app.school.service import School


def create_school_app(
    settings: Settings | None = None, *, gateway: Gateway | None = None
) -> FastAPI:
    settings = settings or get_settings()
    models = gateway or P3Gateway()
    app = create_content_app(settings, gateway=models)
    app.include_router(
        create_router(School(settings.database_url, Repository(lambda: app.state.pool)), models)
    )
    return app
