"""Lab 8 Task 1: audit records. No Azure: the OpenAI client is faked."""
import json
from types import SimpleNamespace

import httpx2 as httpx
import openai
import pytest

from app.ai import advisor_agent, advisor_tools, audit

REQUIRED = {"trace_id", "id", "ts", "event", "actor", "outcome", "model", "tool_calls", "usage",
            "question_hash", "instructions_hash", "deployment", "policy", "retrieved_ids"}


def _lines(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def _response(id_="r1", output=(), text="ok"):
    return SimpleNamespace(id=id_, output=list(output), output_text=text, incomplete_details=None,
                           content_filters=[], model="gpt-4o-2024-11-20", status="completed",
                           usage=SimpleNamespace(input_tokens=10, output_tokens=5))


def _fake_client(*responses, error=None):
    queue = list(responses)

    class Responses:
        def create(self, **kwargs):
            if error:
                raise error
            return queue.pop(0)

    return SimpleNamespace(responses=Responses())


def test_normal_turn_writes_one_record_with_every_field(monkeypatch, _isolated_audit):
    monkeypatch.setattr(advisor_agent, "_client", lambda: _fake_client(_response()))
    advisor_agent.chat_safe("how much on food?", actor="alice")
    [record] = _lines(_isolated_audit)
    assert REQUIRED <= record.keys()
    assert record["actor"] == "alice" and record["outcome"] == "ok"
    assert record["usage"] == {"input": 10, "output": 5}
    assert record["model"] == "gpt-4o-2024-11-20"


def test_two_turns_append_two_lines_and_never_rewrite(monkeypatch, _isolated_audit):
    client = _fake_client(_response("r1"), _response("r2"))
    monkeypatch.setattr(advisor_agent, "_client", lambda: client)
    advisor_agent.chat_safe("one")
    first_line = _isolated_audit.read_text().splitlines()[0]
    advisor_agent.chat_safe("two")
    lines = _isolated_audit.read_text().splitlines()
    assert len(lines) == 2
    assert lines[0] == first_line          # the old line is untouched


def test_blocked_prompt_is_recorded_without_the_prompt_text(monkeypatch, _isolated_audit):
    http = httpx.Response(400, request=httpx.Request("POST", "https://example.test"))
    error = openai.BadRequestError("x", response=http, body={"code": "content_filter"})
    monkeypatch.setattr(advisor_agent, "_client", lambda: _fake_client(error=error))
    advisor_agent.chat_safe("SECRET-BAD-PROMPT")
    raw = _isolated_audit.read_text()
    [record] = _lines(_isolated_audit)
    assert record["outcome"] == "prompt_blocked"
    assert record["question_hash"] == audit.digest("SECRET-BAD-PROMPT")
    assert "SECRET-BAD-PROMPT" not in raw


def test_crash_still_writes_an_error_record(monkeypatch, _isolated_audit):
    monkeypatch.setattr(advisor_agent, "_client", lambda: _fake_client(error=RuntimeError("boom")))
    with pytest.raises(RuntimeError):
        advisor_agent.chat_safe("hi")
    [record] = _lines(_isolated_audit)
    assert record["outcome"] == "error"


def test_tool_calls_and_retrieved_ids_are_recorded_without_result_text(monkeypatch, _isolated_audit):
    call = SimpleNamespace(type="function_call", call_id="c1", name="search_expenses",
                           arguments='{"query": "coffee", "category": null}')
    client = _fake_client(_response("r1", [call]), _response("r2", text="done"))   # build ONCE: it holds the queue
    monkeypatch.setattr(advisor_agent, "_client", lambda: client)
    monkeypatch.setattr(advisor_tools, "retrieve", lambda *a, **k: [
        {"id": "abc", "description": "PRIVATE-LATTE", "category": "Food", "amount": 4.5, "date": "2026-10-02"}])
    advisor_agent.chat_safe("coffee?")
    raw = _isolated_audit.read_text()
    [record] = _lines(_isolated_audit)
    assert record["retrieved_ids"] == ["abc"]
    [tool] = record["tool_calls"]
    assert tool["name"] == "search_expenses" and tool["result_chars"] > 0
    assert "PRIVATE-LATTE" not in raw      # D81: sizes and ids, never content


def test_trace_id_is_none_without_telemetry(monkeypatch, _isolated_audit):
    client = _fake_client(_response())
    monkeypatch.setattr(advisor_agent, "_client", lambda: client)
    advisor_agent.chat_safe("hi")
    assert _lines(_isolated_audit)[0]["trace_id"] is None


def test_trace_id_matches_the_turn_span(monkeypatch, _isolated_audit):
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import SimpleSpanProcessor
    from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

    exporter = InMemorySpanExporter()
    provider = TracerProvider()
    provider.add_span_processor(SimpleSpanProcessor(exporter))
    monkeypatch.setattr(advisor_agent, "_tracer", provider.get_tracer("test"))
    client = _fake_client(_response())
    monkeypatch.setattr(advisor_agent, "_client", lambda: client)
    advisor_agent.chat_safe("hi")
    [span] = exporter.get_finished_spans()
    assert _lines(_isolated_audit)[0]["trace_id"] == format(span.context.trace_id, "032x")
