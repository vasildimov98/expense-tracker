"""chat_safe wiring. No Azure: the OpenAI client is faked."""
from types import SimpleNamespace

import httpx2 as httpx
import openai

from app.ai import advisor_agent
from app.ai.safety import Outcome


def _client_returning(response=None, error=None):
    class Responses:
        def create(self, **kwargs):
            if error:
                raise error
            return response

    return SimpleNamespace(responses=Responses())


def test_chat_safe_returns_text_and_new_response_id(monkeypatch):
    response = SimpleNamespace(id="r2", output=[], output_text="You spent 40.",
                               incomplete_details=None, content_filters=[], usage=None, model="m", status="completed")
    monkeypatch.setattr(advisor_agent, "_client", lambda: _client_returning(response))
    result, next_id = advisor_agent.chat_safe("how much?", "r1")
    assert result.outcome is Outcome.OK and result.text == "You spent 40."
    assert next_id == "r2"


def test_chat_safe_block_keeps_the_previous_conversation_id(monkeypatch):
    http = httpx.Response(400, request=httpx.Request("POST", "https://example.test"))
    error = openai.BadRequestError("x", response=http, body={"code": "content_filter"})
    monkeypatch.setattr(advisor_agent, "_client", lambda: _client_returning(error=error))
    result, next_id = advisor_agent.chat_safe("bad prompt", "r1")
    assert result.outcome is Outcome.PROMPT_BLOCKED
    assert next_id == "r1"      # nothing was added to the conversation


def test_variant_removes_only_the_grounding_sentence():
    default = advisor_agent.instructions_for(None)
    weak = advisor_agent.instructions_for("drop_grounding")
    assert default == advisor_agent.INSTRUCTIONS
    assert advisor_agent.GROUNDING_SENTENCE in default and advisor_agent.GROUNDING_SENTENCE not in weak
    assert "get_spending_summary" in weak          # everything else is untouched


def test_unknown_variant_is_rejected():
    import pytest
    with pytest.raises(ValueError):
        advisor_agent.instructions_for("nonsense")
