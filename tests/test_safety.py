"""Tests for safety.interpret. No Azure: fake responses and real openai exceptions."""
from types import SimpleNamespace

import httpx2 as httpx   # openai 3.x is built on httpx2 (see requirements-ai.txt)
import openai
import pytest

from app.ai.safety import USER_MESSAGES, Outcome, interpret


def bad_request(code, body_extra=None):
    request = httpx.Request("POST", "https://example.test/responses")
    response = httpx.Response(400, request=request)
    body = {"code": code, "message": "x", **(body_extra or {})}
    return openai.BadRequestError("boom", response=response, body=body)


def fake_response(reason=None, text="ok", content_filters=None):
    details = SimpleNamespace(reason=reason) if reason else None
    return SimpleNamespace(incomplete_details=details, output_text=text, content_filters=content_filters)


def raising(error):
    def call():
        raise error
    return call


SELF_HARM_BLOCK = {"content_filters": [{
    "blocked": True, "source_type": "prompt",
    "content_filter_results": {
        "hate": {"filtered": False, "severity": "safe"},
        "self_harm": {"filtered": True, "severity": "medium"},
    },
}]}


def test_ok_passes_text_through():
    result = interpret(lambda: fake_response(text="Food & Dining"))
    assert result.outcome is Outcome.OK
    assert result.text == "Food & Dining"


def test_blocked_prompt_gets_generic_message_and_logs_category():
    result = interpret(raising(bad_request("content_filter", SELF_HARM_BLOCK)))
    assert result.outcome is Outcome.PROMPT_BLOCKED
    assert result.detail["fired"] == {"prompt:self_harm": "medium"}   # for logs only


def test_jailbreak_shield_block_is_logged_as_detected():
    body = {"content_filters": [{
        "blocked": True, "source_type": "prompt",
        "content_filter_results": {"jailbreak": {"detected": True, "filtered": True}},
    }]}
    result = interpret(raising(bad_request("content_filter", body)))
    assert result.outcome is Outcome.PROMPT_BLOCKED
    assert result.detail["fired"] == {"prompt:jailbreak": "detected"}


def test_400_blocked_only_on_completion_is_a_response_filter():
    body = {"content_filters": [{
        "blocked": True, "source_type": "completion",
        "content_filter_results": {"self_harm": {"filtered": True, "severity": "low"}},
    }]}
    result = interpret(raising(bad_request("content_filter", body)))
    assert result.outcome is Outcome.RESPONSE_FILTERED


def test_400_with_both_sources_blocked_counts_as_prompt_block():
    # The real shape the probe printed for the self-harm question.
    body = {"content_filters": [
        {"blocked": True, "source_type": "completion",
         "content_filter_results": {"self_harm": {"filtered": True, "severity": "low"}}},
        {"blocked": True, "source_type": "prompt",
         "content_filter_results": {"self_harm": {"filtered": True, "severity": "medium"}}},
    ]}
    result = interpret(raising(bad_request("content_filter", body)))
    assert result.outcome is Outcome.PROMPT_BLOCKED
    assert result.detail["fired"] == {"completion:self_harm": "low", "prompt:self_harm": "medium"}


def test_response_filtered_by_finish_reason():
    result = interpret(lambda: fake_response(reason="content_filter", text="partial"))
    assert result.outcome is Outcome.RESPONSE_FILTERED
    assert "partial" not in result.text          # the withheld text never reaches the user


def test_response_filtered_by_completion_block_annotation():
    filters = [{"blocked": True, "source_type": "completion",
                "content_filter_results": {"violence": {"filtered": True, "severity": "high"}}}]
    result = interpret(lambda: fake_response(content_filters=filters))
    assert result.outcome is Outcome.RESPONSE_FILTERED
    assert result.detail["fired"] == {"completion:violence": "high"}


def test_truncation_is_not_a_safety_event():
    result = interpret(lambda: fake_response(reason="max_output_tokens", text="half an ans"))
    assert result.outcome is Outcome.TRUNCATED
    assert result.text.startswith("half an ans")


def test_other_bad_request_reraises():
    with pytest.raises(openai.BadRequestError):
        interpret(raising(bad_request("invalid_prompt")))


def test_user_messages_never_leak_filter_internals():
    forbidden = ("filter", "policy", "self_harm", "self-harm", "hate", "violence", "sexual", "jailbreak")
    for message in USER_MESSAGES.values():
        assert not any(word in message.lower() for word in forbidden)
