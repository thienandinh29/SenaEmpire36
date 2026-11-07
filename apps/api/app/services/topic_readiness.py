"""A saved research graph is a checkpoint until its lesson is published."""

import httpx
import psycopg
from fastapi import HTTPException

from app.config import Settings


async def embedding_status(settings: Settings) -> str:
    headers = {}
    if settings.tei_api_key.get_secret_value():
        headers["Authorization"] = "Bearer " + settings.tei_api_key.get_secret_value()
    try:
        async with httpx.AsyncClient(timeout=3, headers=headers) as client:
            response = await client.get(settings.tei_url.rstrip("/") + "/health")
            if response.status_code == 503:
                return "loading"
            if response.status_code != 200:
                return "error"
            info = await client.get(settings.tei_url.rstrip("/") + "/info")
            info.raise_for_status()
            if info.json().get("model_id") != "BAAI/bge-m3":
                return "model_mismatch"
        return "ready"
    except (httpx.HTTPError, ValueError):
        return "unavailable"


async def require_embedding_ready(settings: Settings) -> None:
    status = await embedding_status(settings)
    if status != "ready":
        raise HTTPException(
            503,
            {
                "code": "embedding_" + status,
                "message": (
                    "Embedding chưa sẵn sàng; chưa nhận yêu cầu tạo bài. "
                    "Vui lòng thử lại khi tải model xong."
                ),
            },
        )


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
