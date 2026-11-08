"""Integration checks run only against the suite's isolated PostgreSQL database."""

from pathlib import Path

import psycopg
import pytest

from app.config import Settings
from app.content import runtime
from app.database_status import inspect_database


def test_all_teams_share_the_canonical_migrated_schema(database_url: str) -> None:
    with psycopg.connect(database_url, options="-c default_transaction_read_only=on") as conn:
        status = inspect_database(conn)
        assert status.ready
        assert all(not missing for missing in status.missing_tables.values())
        assert status.embedding_type == "halfvec(1024)"
        assert {
            "chunks",
            "mastery",
            "topic_jobs",
            "p4_hint_cache",
            "learner_api_sessions",
        } <= status.row_counts.keys()


def test_missing_content_table_fails_the_shared_audit(database_url: str) -> None:
    with psycopg.connect(database_url) as conn:
        conn.execute("alter table p4_hint_cache rename to temporarily_missing_hint_cache")
        try:
            status = inspect_database(conn)
            assert not status.ready
            assert status.missing_tables["P4_content"] == ["p4_hint_cache"]
        finally:
            conn.rollback()


def test_pending_migration_fails_preflight(database_url: str, tmp_path: Path) -> None:
    (tmp_path / "9999_pending.sql").write_text("select 1;", encoding="utf-8")
    with psycopg.connect(database_url) as conn:
        status = inspect_database(conn, migrations_dir=tmp_path)
        assert not status.ready
        assert status.missing_migrations == ["9999_pending.sql"]


def test_legacy_content_runtime_uses_shared_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    settings = Settings(_env_file=None, database_url="postgresql://u:p@shared-db:5432/team")
    monkeypatch.setattr(runtime, "get_settings", lambda: settings)
    application = runtime.create_app()
    assert application.state.settings is settings
    assert application.state.graph_confirmations.database_url == settings.database_url
    assert application.state.learner_sessions.database_url == settings.database_url
