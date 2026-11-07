"""Run separately: uv run python -m app.jobs.worker [--fixture]."""

import argparse
import logging
import time

import psycopg

from app.config import get_settings
from app.jobs.queue import claim, finish
from app.observability import configure_logging

logger = logging.getLogger(__name__)


def run_once(database_url: str, *, allow_fixture: bool = False) -> bool:
    with psycopg.connect(database_url) as conn:
        job = claim(conn)
    if job is None:
        return False
    # shortcut: no P3 pipeline yet; only explicitly marked fixtures can finish ready.
    fixture = allow_fixture and job["fixture"]
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
    args = parser.parse_args()
    configure_logging()
    while True:
        try:
            if not run_once(get_settings().database_url, allow_fixture=args.fixture):
                time.sleep(1)
        except Exception:
            logger.exception("worker database failure")
            time.sleep(2)


if __name__ == "__main__":
    main()
