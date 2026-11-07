"""A saved research graph is a checkpoint until its lesson is published."""

import psycopg
from fastapi import HTTPException


def require_published_topic(conn: psycopg.Connection, subject: str) -> None:
    if (
        subject.startswith("topic-")
        and not conn.execute(
            "select 1 from topic_jobs where subject_slug=%s and status='ready' "
            "and graph_ready=true and items_ready=true",
            (subject,),
        ).fetchone()
    ):
        raise HTTPException(
            409, "Bản đồ còn là bản nháp; câu hỏi chưa đủ điều kiện học. Hãy xem tiến độ research."
        )
