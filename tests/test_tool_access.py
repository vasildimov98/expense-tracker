"""Lab 8 Task 3: role allowlist and kill switch, enforced where tools run. Offline."""
import json
from types import SimpleNamespace

import pytest

from app.ai import advisor_agent, advisor_tools, proposals

PROPOSE = json.dumps({"amount": 4.2, "category": "Food", "description": "coffee"})


@pytest.fixture(autouse=True)
def _clean(monkeypatch):
    monkeypatch.setattr(proposals, "_proposals", {})


def _events(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_viewer_cannot_propose_even_when_called_directly(monkeypatch, _isolated_audit):
    monkeypatch.setenv("WRITES_ENABLED", "true")             # even with writes ON
    out = json.loads(advisor_tools.run_tool("propose_expense", PROPOSE, actor="mallory", role="viewer"))
    assert "not available" in out["error"]
    assert proposals._proposals == {}                        # nothing was proposed
    [event] = _events(_isolated_audit)
    assert (event["event"], event["tool"], event["role"], event["reason"]) == \
        ("tool_denied", "propose_expense", "viewer", "role")


def test_editor_is_stopped_by_the_kill_switch(_isolated_audit):
    out = json.loads(advisor_tools.run_tool("propose_expense", PROPOSE, role="editor"))
    assert "not available" in out["error"] and proposals._proposals == {}
    assert _events(_isolated_audit)[-1]["reason"] == "kill_switch"


@pytest.mark.parametrize("value", ["", "false", "TRUE", "1", "yes"])
def test_kill_switch_fails_closed_on_anything_but_true(monkeypatch, value):
    monkeypatch.setenv("WRITES_ENABLED", value)
    out = json.loads(advisor_tools.run_tool("propose_expense", PROPOSE, role="editor"))
    assert "error" in out and proposals._proposals == {}


def test_editor_with_writes_enabled_can_propose(monkeypatch):
    monkeypatch.setenv("WRITES_ENABLED", "true")
    out = json.loads(advisor_tools.run_tool("propose_expense", PROPOSE, role="editor"))
    assert out["status"] == "pending_approval"


def test_kill_switch_does_not_stop_reads(monkeypatch):
    monkeypatch.setitem(advisor_tools.IMPLEMENTATIONS, "get_spending_summary", lambda: {"total": 1})
    assert advisor_tools.run_tool("get_spending_summary", "{}", role="viewer") == '{"total": 1}'


def test_unknown_role_is_denied_everything(_isolated_audit):
    denied = advisor_tools.run_tool("get_spending_summary", "{}", role="viewr")   # a typo
    assert "not available" in json.loads(denied)["error"]
    assert _events(_isolated_audit)[-1]["role"] == "viewr"


def test_unknown_tool_is_denied_and_audited_with_a_capped_name(_isolated_audit):
    advisor_tools.run_tool("x" * 500, "{}", role="editor")
    event = _events(_isolated_audit)[-1]
    assert event["event"] == "tool_denied" and len(event["tool"]) == 64


def test_malformed_arguments_are_data_not_a_crash(monkeypatch):
    monkeypatch.setenv("WRITES_ENABLED", "true")
    out = json.loads(advisor_tools.run_tool("propose_expense", "{not json", role="editor"))
    assert "error" in out


def test_the_role_travels_from_chat_safe_to_run_tool(monkeypatch, _isolated_audit):
    monkeypatch.setenv("WRITES_ENABLED", "true")
    call = SimpleNamespace(type="function_call", call_id="c1", name="propose_expense", arguments=PROPOSE)
    final = SimpleNamespace(id="r2", output=[], output_text="no", incomplete_details=None, content_filters=[],
                            model="m", status="completed", usage=None)
    first = SimpleNamespace(id="r1", output=[call], output_text="", incomplete_details=None, content_filters=[],
                            model="m", status="completed", usage=None)
    queue = [first, final]
    client = SimpleNamespace(responses=SimpleNamespace(create=lambda **kw: queue.pop(0)))
    monkeypatch.setattr(advisor_agent, "_client", lambda: client)
    advisor_agent.chat_safe("add coffee", actor="alice", role="viewer")
    events = _events(_isolated_audit)
    assert [e["event"] for e in events] == ["tool_denied", "agent_turn"]
    assert events[1]["role"] == "viewer" and proposals._proposals == {}


def test_events_inside_a_turn_span_carry_its_trace_id(monkeypatch, _isolated_audit):
    from opentelemetry.sdk.trace import TracerProvider

    tracer = TracerProvider().get_tracer("test")
    with tracer.start_as_current_span("advisor.turn") as span:
        advisor_tools.run_tool("propose_expense", PROPOSE, role="viewer")
    event = _events(_isolated_audit)[-1]
    assert event["event"] == "tool_denied" and event["trace_id"] == format(span.get_span_context().trace_id, "032x")


def test_events_outside_a_span_have_no_trace_id(_isolated_audit):
    advisor_tools.run_tool("propose_expense", PROPOSE, role="viewer")
    assert "trace_id" not in _events(_isolated_audit)[-1]
