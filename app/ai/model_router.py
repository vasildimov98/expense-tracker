"""Maps a task to the cheapest deployment that meets its quality bar."""
import os
from functools import lru_cache

from app.ai.foundry_client import get_openai_client

# Task -> env var holding the deployment name. Config, not code (D19).
_ROUTES = {
    "categorize": "FOUNDRY_MODEL_DEPLOYMENT",    # high volume, simple: small model
    "advise": "FOUNDRY_ADVISOR_DEPLOYMENT",      # low volume, reasoning: large model
}


@lru_cache(maxsize=1)
def _client():
    # Build the credential and client once, not on every call.
    return get_openai_client()


def deployment_for(task: str) -> str:
    try:
        return os.environ[_ROUTES[task]]
    except KeyError:
        raise ValueError(f"Unknown task or missing config: {task!r}") from None


def ask(task: str, instructions: str, user_input: str, max_output_tokens: int) -> str:
    response = _client().responses.create(
        model=deployment_for(task),
        instructions=instructions,
        input=user_input,
        max_output_tokens=max_output_tokens,
    )
    return response.output_text