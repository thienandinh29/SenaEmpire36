"""Run separately: uv run python -m app.jobs.worker [--fixture]."""

import argparse
import asyncio
import logging
import time
from collections.abc import Callable
from typing import Any

import psycopg

from app.config import get_settings
from app.jobs.queue import claim, finish
from app.observability import configure_logging

logger = logging.getLogger(__name__)


def run_once(
    database_url: str,
    *,
    allow_fixture: bool = False,
    processor: Callable[[dict[str, Any]], None] | None = None,
) -> bool:
    with psycopg.connect(database_url) as conn:
        job = claim(conn)
    if job is None:
        return False
    fixture = allow_fixture and job["fixture"]
    if processor is not None and not job["fixture"]:
        # The queue claim has committed before long P3/P4 work starts.
        processor(job)
        return True
    with psycopg.connect(database_url) as conn:
        finish(conn, job["id"], fixture=fixture)
    logger.log(
        logging.INFO if fixture else logging.ERROR,
        "fixture completed" if fixture else "P3 pipeline unavailable",
        extra={"topic_id": str(job["id"]), "tier": job["tier"]},
    )
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", action="store_true")
    parser.add_argument(
        "--pipeline", action="store_true", help="Use configured P4/P3 content ports"
    )
    args = parser.parse_args()
    configure_logging()
    if args.pipeline:
        from app.content.gateway import P3Gateway
        from app.content.ports import process_claimed_job
        from app.content.repository import Repository
        from app.db import create_pool

        with create_pool(get_settings().database_url) as pool:
            repository = Repository(lambda: pool)
            repository.require_schema()
            gateway = P3Gateway()

            def process(job: dict[str, Any]) -> None:
                asyncio.run(process_claimed_job(repository, gateway, job))

            loop(get_settings().database_url, allow_fixture=args.fixture, processor=process)
        return
    loop(get_settings().database_url, allow_fixture=args.fixture)


def loop(
    database_url: str,
    *,
    allow_fixture: bool,
    processor: Callable[[dict[str, Any]], None] | None = None,
) -> None:
    while True:
        try:
            if not run_once(database_url, allow_fixture=allow_fixture, processor=processor):
                time.sleep(1)
        except Exception:
            logger.exception("worker database failure")
            time.sleep(2)


if __name__ == "__main__":
    main()
