"""Tests for call_with_retry. No Azure, no real waiting: sleep and now are fakes."""
import httpx2 as httpx   # this openai version is built on httpx2
import openai
import pytest

from app.ai import resilience
from app.ai.resilience import call_with_retry


def make_429(retry_after: str | None = None) -> openai.RateLimitError:
    """Build a RateLimitError like the one the SDK raises on an HTTP 429."""
    headers = {"retry-after": retry_after} if retry_after is not None else {}
    request = httpx.Request("POST", "https://example.invalid/responses")
    response = httpx.Response(429, headers=headers, request=request)
    return openai.RateLimitError("rate limited", response=response, body=None)


class FakeClock:
    """Records every sleep and moves 'now' forward instead of really waiting."""

    def __init__(self):
        self.time = 0.0
        self.sleeps: list[float] = []

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.time += seconds

    def now(self) -> float:
        return self.time


@pytest.fixture
def clock():
    return FakeClock()


def run(fn, deployments, clock):
    return call_with_retry(fn, deployments, sleep=clock.sleep, now=clock.now)


def test_succeeds_on_third_attempt_without_failover(clock):
    calls = []

    def fn(deployment):
        calls.append(deployment)
        if len(calls) < 3:
            raise make_429()
        return "answer"

    assert run(fn, ["primary", "fallback"], clock) == "answer"
    assert calls == ["primary", "primary", "primary"]   # fallback never used
    assert len(clock.sleeps) == 2                       # waited before attempts 2 and 3


def test_fails_over_when_primary_stays_throttled(clock):
    def fn(deployment):
        if deployment == "primary":
            raise make_429()
        return f"answer from {deployment}"

    assert run(fn, ["primary", "fallback"], clock) == "answer from fallback"


def test_honors_retry_after_header(clock):
    calls = []

    def fn(deployment):
        calls.append(deployment)
        if len(calls) == 1:
            raise make_429(retry_after="3")
        return "ok"

    run(fn, ["primary"], clock)
    assert clock.sleeps == [3.0]       # exactly what the server asked for, no jitter


def test_raises_last_error_when_everything_is_throttled(clock):
    def fn(deployment):
        raise make_429()

    with pytest.raises(openai.RateLimitError):
        run(fn, ["primary", "fallback"], clock)


def test_does_not_retry_other_errors(clock):
    calls = []

    def fn(deployment):
        calls.append(deployment)
        raise ValueError("a bug, not throttling")

    with pytest.raises(ValueError):
        run(fn, ["primary", "fallback"], clock)
    assert calls == ["primary"]        # one attempt, no retry, no failover
    assert clock.sleeps == []


def test_stops_retrying_when_time_budget_is_spent(clock, monkeypatch):
    monkeypatch.setattr(resilience, "TOTAL_BUDGET", 5.0)
    calls = []

    def fn(deployment):
        calls.append(deployment)
        raise make_429(retry_after="10")   # one wait already exceeds the budget

    with pytest.raises(openai.RateLimitError):
        run(fn, ["primary"], clock)
    assert calls == ["primary"]        # gave up instead of sleeping 10 s
    assert clock.sleeps == []


def make_timeout() -> openai.APITimeoutError:
    return openai.APITimeoutError(request=httpx.Request("POST", "https://example.invalid/responses"))


def test_timeout_is_retried_and_can_fail_over(clock):
    def fn(deployment):
        if deployment == "primary":
            raise make_timeout()          # the service held the request and never answered
        return "from fallback"

    assert run(fn, ["primary", "fallback"], clock) == "from fallback"


def test_connection_errors_other_than_timeout_are_not_retried(clock):
    calls = []

    def fn(deployment):
        calls.append(deployment)
        raise openai.APIConnectionError(request=httpx.Request("POST", "https://example.invalid"))

    with pytest.raises(openai.APIConnectionError):
        run(fn, ["primary", "fallback"], clock)
    assert calls == ["primary"]
