import httpx

from app.llm.providers import http_failure


def test_rate_limit_is_not_assumed_to_be_daily_quota() -> None:
    error = http_failure(httpx.Response(429, headers={"Retry-After": "35"}))
    assert error.retry_after == 35
    assert error.retryable
    assert error.failure_kind == "transient"


def test_daily_quota_stops_retries_without_exposing_provider_text() -> None:
    response = httpx.Response(
        429,
        json={
            "error": {
                "message": "private",
                "details": [{"violations": [{"quotaId": "GenerateRequestsPerDayPerProject"}]}],
            }
        },
    )
    error = http_failure(response)
    assert error.failure_kind == "quota"
    assert not error.retryable
    assert str(error) == "http_429"


def test_invalid_credentials_are_not_retried() -> None:
    error = http_failure(httpx.Response(403))
    assert error.failure_kind == "configuration"
    assert not error.retryable
