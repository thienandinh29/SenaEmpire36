"""Committed queue claims and durable topic snapshots, independent of P3."""

from typing import Any
from uuid import UUID

import psycopg
from psycopg.rows import dict_row

FIELDS = "status, step_vi, progress, subject_slug, graph_ready, items_ready, sources, trail"


def enqueue(
    conn: psycopg.Connection[Any], goal_vi: str, tier: str, *, fixture: bool = False
) -> UUID:
    if not goal_vi.strip():
        raise ValueError("goal_vi must not be blank")
    row = conn.execute(
        "insert into topic_jobs(goal_vi,tier,fixture) values (%s,%s,%s) returning id",
        (goal_vi, tier, fixture),
    ).fetchone()
    assert row is not None
    return row[0]  # type: ignore[no-any-return]


def claim(conn: psycopg.Connection[Any]) -> dict[str, Any] | None:
    """Caller commits before executing long work; competing workers skip locked rows."""
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            "update topic_jobs set status='researching', step_vi='Đang xử lý', updated_at=now() "
            "where id=(select id from topic_jobs where status='queued' "
            "order by created_at,id for update skip locked limit 1) returning *"
        )
        return cur.fetchone()


def snapshot(conn: psycopg.Connection[Any], topic_id: UUID) -> dict[str, Any] | None:
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"select {FIELDS} from topic_jobs where id=%s", (topic_id,))
        return cur.fetchone()


def finish(conn: psycopg.Connection[Any], topic_id: UUID, *, fixture: bool) -> None:
    conn.execute(
        "update topic_jobs set status=%s, step_vi=%s, progress=%s, updated_at=now() "
        "where id=%s and status='researching'",
        (
            "ready" if fixture else "failed",
            "Dữ liệu mô phỏng; chưa có nội dung học" if fixture else "Chưa có pipeline từ P3",
            100 if fixture else 0,
            topic_id,
        ),
    )
