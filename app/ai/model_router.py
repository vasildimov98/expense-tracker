"""Maps a task to the cheapest deployment that meets its quality bar."""
import os
import time
from functools import lru_cache

from app.ai import usage
from app.ai.foundry_client import get_openai_client
from app.ai.resilience import call_with_retry
from app.ai.safety import SafeResult, interpret

# Task -> env var holding the deployment name. Config, not code (D19).
_ROUTES = {
    "categorize": "FOUNDRY_MODEL_DEPLOYMENT",    # high volume, simple: small model
    "advise": "FOUNDRY_ADVISOR_DEPLOYMENT",      # low volume, reasoning: large model
}


@lru_cache(maxsize=1)
def _client():
    # Build the credential and client once, not on every call.
    # max_retries=0: our call_with_retry is the ONLY retry layer. If the SDK
    # also retried, the two layers would multiply attempts and waits.
    # timeout=30: without it a stalled request can hang for minutes, and no
    # retry logic can help because nothing is ever raised.
    return get_openai_client().with_options(max_retries=0, timeout=30.0)


def deployment_for(task: str) -> str:
    try:
        return os.environ[_ROUTES[task]]
    except KeyError:
        raise ValueError(f"Unknown task or missing config: {task!r}") from None


def fallbacks_for(task: str) -> list[str]:
    """Optional failover deployments, from FOUNDRY_FALLBACK_<TASK> (comma-separated).

    Empty or unset means no failover. Config, not code (D19).
    """
    raw = os.environ.get(f"FOUNDRY_FALLBACK_{task.upper()}", "")
    return [name.strip() for name in raw.split(",") if name.strip()]


def _respond(task: str, instructions: str, user_input: str, max_output_tokens: int):
    usage.check_cap()   # fail closed BEFORE spending anything (D61)

    def call(deployment: str):
        started = time.monotonic()
        response = _client().responses.create(
            model=deployment,   # deployment NAME, as always
            instructions=instructions,
            input=user_input,
            max_output_tokens=max_output_tokens,
        )
        # Only successful attempts reach here, so throttled tries are not logged.
        usage.record_response(task, deployment, response, time.monotonic() - started)
        return response

    return call_with_retry(call, [deployment_for(task), *fallbacks_for(task)])


def ask(task: str, instructions: str, user_input: str, max_output_tokens: int) -> str:
    return _respond(task, instructions, user_input, max_output_tokens).output_text


def ask_safe(task: str, instructions: str, user_input: str, max_output_tokens: int) -> SafeResult:
    """ask() that treats content-filter outcomes as results, not crashes (D73).

    A blocked prompt is a 400, which call_with_retry does not retry: retrying it would be blocked again.
    """
    result = interpret(lambda: _respond(task, instructions, user_input, max_output_tokens))
    usage.record_outcome(task, result.outcome.value, result.detail)
    return result
