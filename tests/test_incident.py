"""Lab 8 Task 5: the incident reader, on synthetic audit records. Offline."""
from app.ai.labs import lab08_incident as inc


def rec(event, ts, **fields):
    return {"event": event, "ts": ts, "actor": fields.pop("actor", "x"), **fields}


CLEAN = [
    rec("proposal_created", 100, actor="agent-user", proposal_id="p1"),
    rec("proposal_approved", 160, actor="alice", proposal_id="p1", proposer="agent-user"),
    rec("proposal_executed", 161, actor="alice", proposal_id="p1"),
]


def test_q1_chain_names_proposer_approver_and_the_gap():
    chain = inc.last_executed_chain(CLEAN)
    assert chain["proposer"] == "agent-user" and chain["approver"] == "alice"
    assert chain["seconds_proposal_to_approval"] == 60 and chain["seconds_approval_to_execution"] == 1


def test_q1_without_any_execution_is_none():
    assert inc.last_executed_chain([rec("proposal_created", 1, proposal_id="p")]) is None


def test_q2_q3_pick_the_turn_at_or_before_the_timestamp():
    turns = [rec("agent_turn", 10, model_version="v1", instructions_hash="a", retrieved_ids=["r1"]),
             rec("agent_turn", 20, model_version="v2", instructions_hash="b", retrieved_ids=["r2"])]
    assert inc.turn_at(turns, 15)["model_version"] == "v1"
    assert inc.turn_at(turns, 25)["retrieved_ids"] == ["r2"]
    assert inc.turn_at(turns, None)["instructions_hash"] == "b"
    assert inc.turn_at(turns, 5) is None


def test_q4_only_denials_inside_the_window():
    events = [rec("tool_denied", 4000, role="viewer", tool="propose_expense", reason="role"),
              rec("tool_denied", 100, role="viewer", tool="old", reason="role"),
              rec("agent_turn", 4000)]
    found = inc.denied_since(events, seconds=3600, now=5000)
    assert [(d["role"], d["tool"], d["reason"]) for d in found] == [("viewer", "propose_expense", "role")]


def test_q5_clean_log_has_no_violations():
    assert inc.integrity_violations(CLEAN) == []


def test_q5_finds_execution_without_approval():
    forged = [rec("proposal_executed", 5, proposal_id="evil")]
    assert inc.integrity_violations(forged)[0]["problem"].startswith("executed without")


def test_q5_finds_approval_that_came_after_execution_and_double_execution():
    late = [rec("proposal_executed", 5, proposal_id="p"), rec("proposal_approved", 9, proposal_id="p")]
    assert inc.integrity_violations(late)
    twice = CLEAN + [rec("proposal_executed", 200, proposal_id="p1")]
    assert any("more than once" in p["problem"] for p in inc.integrity_violations(twice))
