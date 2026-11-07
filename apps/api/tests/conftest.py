import os
import uuid
from collections.abc import Iterator

import psycopg
import pytest
from psycopg import sql

from app.migrate import apply_migrations

# Admin connection to the local Docker server; tests create and drop their own database.
ADMIN_URL = os.environ.get(
    "TEST_DATABASE_ADMIN_URL", "postgresql://postgres:postgres@localhost:54322/postgres"
)


@pytest.fixture(scope="session")
def database_url() -> Iterator[str]:
    """A throwaway, fully migrated database so tests never touch dev or demo data."""
    name = f"nodetrail_test_{uuid.uuid4().hex[:8]}"
    try:
        admin = psycopg.connect(ADMIN_URL, autocommit=True, connect_timeout=3)
    except psycopg.OperationalError as exc:
        pytest.fail(f"Test database server unreachable ({exc}). Run: docker compose up -d")
    with admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(name)))
        url = ADMIN_URL.rsplit("/", 1)[0] + f"/{name}"
        try:
            apply_migrations(url)
            yield url
        finally:
            admin.execute(sql.SQL("drop database {} with (force)").format(sql.Identifier(name)))
