import pytest

from app.config import Settings


def test_blank_env_value_falls_back_to_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")
    settings = Settings(_env_file=None)
    assert settings.database_url.endswith("localhost:54322/nodetrail")


def test_env_value_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql://u:p@example:5432/db")
    settings = Settings(_env_file=None)
    assert settings.database_url == "postgresql://u:p@example:5432/db"
