"""Read-only audit of the shared database used by all team components.

Run `python -m app.database_status`; connection credentials and row contents are
never included in the report. Canonical migrations live in supabase/migrations.
"""

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import psycopg
from psycopg import sql

from app.config import get_settings
from app.migrate import MIGRATIONS_DIR

TEAM_TABLES = {
    "P1_learning_retrieval": (
        "subjects",
        "sources",
        "chunks",
        "concepts",
        "concept_edges",
        "concept_sources",
        "mastery",
        "review_cards",
        "decision_traces",
    ),
    "P2_platform": ("learners", "uploads", "attempts", "attempt_replays"),
    "P3_research": ("topic_jobs", "llm_calls"),
    "P4_content": (
        "items",
        "item_options",
        "misconceptions",
        "p4_hint_cache",
        "p4_learning_sessions",
        "p4_verification_history",
    ),
    "P5_sessions": ("learner_graph_confirmations", "learner_api_sessions"),
}


@dataclass(frozen=True)
class DatabaseStatus:
    host: str
    port: int
    database: str
    missing_tables: dict[str, list[str]]
    missing_migrations: list[str]
    embedding_type: str | None
    unvalidated_foreign_keys: list[str]
    row_counts: dict[str, int]

    @property
    def ready(self) -> bool:
        return (
            not any(self.missing_tables.values())
            and not self.missing_migrations
            and self.embedding_type == "halfvec(1024)"
            and not self.unvalidated_foreign_keys
        )


def inspect_database(
    connection: psycopg.Connection[Any], *, migrations_dir: Path = MIGRATIONS_DIR
) -> DatabaseStatus:
    """Inspect metadata and counts only; never migrate, seed or modify records."""
    existing = {
        row[0]
        for row in connection.execute("select tablename from pg_tables where schemaname='public'")
    }
    missing_tables = {
        team: [table for table in tables if table not in existing]
        for team, tables in TEAM_TABLES.items()
    }
    applied = (
        {row[0] for row in connection.execute("select name from public.schema_migrations")}
        if "schema_migrations" in existing
        else set()
    )
    missing_migrations = [
        path.name for path in sorted(migrations_dir.glob("*.sql")) if path.name not in applied
    ]
    embedding = connection.execute(
        "select format_type(a.atttypid,a.atttypmod) from pg_attribute a "
        "where a.attrelid=to_regclass('public.chunks') and a.attname='embedding' "
        "and not a.attisdropped"
    ).fetchone()
    invalid_keys = [
        row[0]
        for row in connection.execute(
            "select c.conname from pg_constraint c join pg_namespace n on n.oid=c.connamespace "
            "where n.nspname='public' and c.contype='f' and not c.convalidated order by c.conname"
        )
    ]
    counts = {}
    for table in sorted({table for tables in TEAM_TABLES.values() for table in tables} & existing):
        row = connection.execute(
            sql.SQL("select count(*) from public.{}").format(sql.Identifier(table))
        ).fetchone()
        assert row is not None
        counts[table] = row[0]
    return DatabaseStatus(
        host=connection.info.host,
        port=connection.info.port,
        database=connection.info.dbname,
        missing_tables=missing_tables,
        missing_migrations=missing_migrations,
        embedding_type=embedding[0] if embedding else None,
        unvalidated_foreign_keys=invalid_keys,
        row_counts=counts,
    )


def main() -> int:
    settings = get_settings()
    try:
        with psycopg.connect(
            settings.database_url,
            connect_timeout=3,
            options="-c default_transaction_read_only=on",
        ) as connection:
            status = inspect_database(connection)
        print(json.dumps({"ready": status.ready, **asdict(status)}, ensure_ascii=False, indent=2))
        return 0 if status.ready else 1
    except psycopg.Error:
        # Driver exceptions can contain the DSN; keep their contents private.
        print(
            json.dumps(
                {"ready": False, "error": "Database audit failed; check DATABASE_URL and access."}
            )
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
