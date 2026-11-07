import asyncio

import pytest

from app.llm.gateway import Gateway
from app.llm.smoke import configuration, probe
from tests.llm.test_gateway import Fake, routes


def test_configuration_never_reveals_environment_values(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("OPENROUTER_API_KEY", "not-for-logs")
    report = configuration(routes())
    assert report and all(row["model_configured"] for row in report)
    assert "not-for-logs" not in str(report)


def test_provider_probe_does_not_hide_failure_with_fallback() -> None:
    fake = Fake(['{"text_vi":"Kết nối thành công."}'])
    report = asyncio.run(probe(Gateway(routes(), {"vertex": fake}), "vertex", "free", "items"))
    assert report["provider"] == "vertex" and report["status"] == "ok"
    assert fake.models == ["gemini-test"]
