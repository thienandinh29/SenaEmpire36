"""Run the real web/API/worker with repository settings, without copying secrets.

Use apps/api/.venv/Scripts/python.exe scripts/run_live.py --service check first.
"""

import argparse
import os
import shutil
import socket
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
API = ROOT / "apps" / "api"
sys.path.insert(0, str(API))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", choices=["check", "web", "api", "worker"], default="check")
    parser.add_argument("--api-url", default="http://127.0.0.1:8000")
    parser.add_argument("--web-port", type=int, default=3000)
    parser.add_argument("--reload", action="store_true", help="Reload API code during development")
    parser.add_argument(
        "--local-uploads",
        action="store_true",
        help="Enable consented demo uploads in private workspace storage",
    )
    args = parser.parse_args()
    if args.local_uploads:
        os.environ["DEMO_UPLOADS_ENABLED"] = "true"
        os.environ["LOCAL_UPLOAD_DIR"] = str(ROOT / ".local" / "private-uploads")

    from pydantic import ValidationError

    # isort: split
    from app.config import Settings

    try:
        settings = Settings()
    except ValidationError as exc:
        print(
            "Invalid configuration fields:",
            ", ".join(str(e["loc"][0]) for e in exc.errors()),
        )
        return 1
    if not settings.api_key.strip():
        print("Set API_KEY in the repository .env before starting the live application.")
        return 1

    if args.service == "web":
        node = shutil.which("node")
        if not node:
            print("Node.js is required.")
            return 1
        # The web process receives the shared proxy key, never model/database secrets.
        environment = os.environ.copy()
        environment.update(
            NODETRAIL_DATA_MODE="api",
            NODETRAIL_API_URL=args.api_url,
            NODETRAIL_API_KEY=settings.api_key,
            NODETRAIL_API_KEY_HEADER="X-API-Key",
        )
        return subprocess.call(
            [
                node,
                str(ROOT / "apps/web/node_modules/next/dist/bin/next"),
                "dev",
                "--hostname",
                "127.0.0.1",
                "--port",
                str(args.web_port),
            ],
            cwd=ROOT / "apps/web",
            env=environment,
        )

    available = True
    for name, url, default_port in [
        ("PostgreSQL", settings.database_url, 5432),
        ("bge-m3 TEI", settings.tei_url, 80),
    ]:
        endpoint = urlsplit(url)
        try:
            with socket.create_connection(
                (endpoint.hostname or "localhost", endpoint.port or default_port),
                timeout=3,
            ):
                print(f"{name}: reachable")
        except OSError:
            print(
                f"{name}: unavailable; start the configured service before running the API/worker."
            )
            available = False
    if not available:
        print("With Docker installed, run: docker compose up -d --wait db tei")
        print("Then apply local migrations: cd apps/api && .venv/Scripts/python -m app.migrate")
        return 1

    if args.service == "check":
        import httpx
        import psycopg

        # isort: split
        from app.database_status import inspect_database

        try:
            with psycopg.connect(settings.database_url, connect_timeout=3) as connection:
                status = inspect_database(connection)
                if not status.ready:
                    print("Shared database schema is incomplete for one or more teams.")
                    print("Run: cd apps/api && .venv/Scripts/python -m app.database_status")
                    return 1
                print(f"Shared database: {status.host}:{status.port}/{status.database}")
            headers = {}
            if settings.tei_api_key.get_secret_value():
                headers["Authorization"] = "Bearer " + settings.tei_api_key.get_secret_value()
            with httpx.Client(timeout=10, headers=headers) as client:
                result = client.get(settings.tei_url.rstrip("/") + "/health")
                result.raise_for_status()
            print(
                "Database schema and embedding health check passed. No sample content was inserted."
            )
            return 0
        except (psycopg.Error, httpx.HTTPError):
            print("Database schema or embedding health check failed. Check service configuration.")
            return 1

    command = (
        [
            sys.executable,
            "-m",
            "uvicorn",
            "app.main:create_content_app",
            "--factory",
            *(["--reload", "--reload-dir", str(API / "app")] if args.reload else []),
            "--host",
            "127.0.0.1",
            "--port",
            "8000",
        ]
        if args.service == "api"
        else [sys.executable, "-m", "app.jobs.worker", "--pipeline"]
    )
    environment = os.environ.copy()
    # Pin both child processes to the database that passed the shared preflight.
    environment["DATABASE_URL"] = settings.database_url
    return subprocess.call(command, cwd=API, env=environment)


if __name__ == "__main__":
    raise SystemExit(main())
