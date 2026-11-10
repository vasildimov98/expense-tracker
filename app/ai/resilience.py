"""Retry with backoff on 429, then fail over to a fallback deployment."""
import random
import time
from typing import Callable, TypeVar

import openai

T = TypeVar("T")

MAX_ATTEMPTS = 4          # per deployment
BASE_DELAY = 1.0          # seconds
MAX_DELAY = 20.0
TOTAL_BUDGET = 45.0       # a user never waits longer than this


def _delay(attempt: int, retry_after: float | None) -> float:
    if retry_after is not None:               # the server knows best
        return min(retry_after, MAX_DELAY)
    backoff = min(MAX_DELAY, BASE_DELAY * 2 ** attempt)
    return random.uniform(0, backoff)          # full jitter


def _retry_after(error: openai.RateLimitError) -> float | None:
    value = error.response.headers.get("retry-after")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def call_with_retry(
    fn: Callable[[str], T],
    deployments: list[str],
    sleep: Callable[[float], None] | None = None,
    now: Callable[[], float] | None = None,
) -> T:
    """fn(deployment_name) is tried on each deployment in order."""
    # Resolved at call time (not as default arguments) so tests can patch time.
    sleep = sleep or time.sleep
    now = now or time.monotonic
    started = now()
    last_error: Exception | None = None
    for deployment in deployments:
        for attempt in range(MAX_ATTEMPTS):
            try:
                return fn(deployment)
            except openai.RateLimitError as error:
                last_error = error
                wait = _delay(attempt, _retry_after(error))
                if now() - started + wait > TOTAL_BUDGET:
                    break                      # give up on this deployment
                sleep(wait)
    raise last_error or RuntimeError("no deployments configured")
