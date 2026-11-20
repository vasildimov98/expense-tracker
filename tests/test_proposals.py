"""Lab 8 Task 2a: propose() and its constraints. Offline."""
import json

import pytest

from app.ai import proposals

GOOD = {"amount": 4.2, "category": "Food", "description": "coffee"}


@pytest.fixture(autouse=True)
def _clean_state(monkeypatch):
    monkeypatch.setattr(proposals, "_proposals", {})      # module state must not leak between tests


def _events(path):
    return [json.loads(line) for line in path.read_text().splitlines()]


def test_happy_path_creates_a_pending_proposal_and_audits_it(_isolated_audit):
    p = proposals.propose("alice", dict(GOOD))
    assert p.status == "pending" and p.digest == proposals.payload_digest(GOOD)
    [event] = _events(_isolated_audit)
    assert event["event"] == "proposal_created" and event["proposal_id"] == p.id


@pytest.mark.parametrize("payload, reason", [
    ({**GOOD, "amount": 9000}, "exceeds"),
    ({**GOOD, "amount": -5}, "positive"),
    ({**GOOD, "amount": True}, "positive"),             # bool is an int in Python: easy to miss
    ({**GOOD, "category": "Crypto"}, "category"),
])
def test_constraints_reject_and_audit_the_reason(payload, reason, _isolated_audit):
    with pytest.raises(proposals.ProposalRejected, match=reason):
        proposals.propose("alice", payload)
    [event] = _events(_isolated_audit)
    assert event["event"] == "proposal_rejected" and reason in event["reason"]
    assert "coffee" not in _isolated_audit.read_text()   # D81: no payload content
    assert proposals._proposals == {}                    # nothing was stored


def test_rate_limit_is_per_actor_and_slides(monkeypatch):
    clock = [1_000_000.0]
    monkeypatch.setattr(proposals, "_now", lambda: clock[0])
    for _ in range(proposals.PROPOSALS_PER_HOUR):
        proposals.propose("alice", dict(GOOD))
    with pytest.raises(proposals.ProposalRejected, match="rate limit"):
        proposals.propose("alice", dict(GOOD))
    proposals.propose("bob", dict(GOOD))                 # another actor is unaffected
    clock[0] += proposals.RATE_WINDOW_SECONDS + 1        # the hour slides past
    proposals.propose("alice", dict(GOOD))


# ---- approve / reject / execute -------------------------------------------------------------

class FakeService:
    def __init__(self, fail=False):
        self.added, self.fail = [], fail

    def add_expense(self, category, amount, description):
        if self.fail:
            raise OSError("disk full")
        self.added.append((category, amount, description))


def _pending(actor="alice"):
    return proposals.propose(actor, dict(GOOD))


def test_happy_path_propose_approve_execute(_isolated_audit):
    p = _pending()
    service = FakeService()
    proposals.approve(p.id, p.digest, "bob")
    proposals.execute(p.id, service)
    assert p.status == "executed" and len(service.added) == 1
    assert [e["event"] for e in _events(_isolated_audit)] == [
        "proposal_created", "proposal_approved", "proposal_executed"]


def test_approve_with_wrong_digest_is_denied(_isolated_audit):
    p = _pending()
    with pytest.raises(proposals.ApprovalError, match="digest"):
        proposals.approve(p.id, "0000000000000000", "bob")
    assert p.status == "pending" and _events(_isolated_audit)[-1]["event"] == "approval_denied"


def test_approve_own_proposal_is_denied():
    p = _pending("alice")
    with pytest.raises(proposals.ApprovalError, match="proposer"):
        proposals.approve(p.id, p.digest, "alice")


def test_approve_expired_is_denied_and_marked(monkeypatch):
    clock = [1_000_000.0]
    monkeypatch.setattr(proposals, "_now", lambda: clock[0])
    p = _pending()
    clock[0] += proposals.EXPIRY_SECONDS + 1
    with pytest.raises(proposals.ApprovalError, match="expired"):
        proposals.approve(p.id, p.digest, "bob")
    assert p.status == "expired"


def test_unknown_and_already_approved_are_denied():
    with pytest.raises(proposals.ApprovalError, match="unknown"):
        proposals.approve("nope", "x", "bob")
    p = _pending()
    proposals.approve(p.id, p.digest, "bob")
    with pytest.raises(proposals.ApprovalError, match="not pending"):
        proposals.approve(p.id, p.digest, "carol")          # no second approval, no replay


def test_execute_requires_approval_and_runs_once():
    p = _pending()
    service = FakeService()
    with pytest.raises(proposals.ApprovalError, match="not approved"):
        proposals.execute(p.id, service)
    proposals.approve(p.id, p.digest, "bob")
    proposals.execute(p.id, service)
    with pytest.raises(proposals.ApprovalError, match="executed"):
        proposals.execute(p.id, service)                    # idempotent: the second call raises
    assert len(service.added) == 1


def test_payload_edited_after_approval_does_not_execute():
    p = _pending()
    proposals.approve(p.id, p.digest, "bob")
    p.payload["amount"] = 499.0                             # approve one thing, execute another
    service = FakeService()
    with pytest.raises(proposals.ApprovalError, match="changed"):
        proposals.execute(p.id, service)
    assert service.added == []


def test_failed_write_leaves_the_proposal_retryable(_isolated_audit):
    p = _pending()
    proposals.approve(p.id, p.digest, "bob")
    with pytest.raises(OSError):
        proposals.execute(p.id, FakeService(fail=True))
    assert p.status == "approved" and _events(_isolated_audit)[-1]["event"] == "proposal_execute_failed"
    proposals.execute(p.id, FakeService())
    assert p.status == "executed"


def test_human_reject_blocks_approval():
    p = _pending()
    proposals.reject(p.id, "bob")
    with pytest.raises(proposals.ApprovalError, match="not pending"):
        proposals.approve(p.id, p.digest, "carol")


# ---- persistence, tool and review CLI -------------------------------------------------------

@pytest.fixture
def shared_file(tmp_path, monkeypatch):
    monkeypatch.setattr(proposals, "PROPOSALS_PATH", str(tmp_path / "proposals.json"))


def test_state_survives_a_fresh_process(shared_file):
    p = _pending()
    proposals._proposals.clear()                      # a new process starts with an empty dict
    assert [x.id for x in proposals.list_pending()] == [p.id]
    proposals.approve(p.id, p.digest, "bob")
    proposals._proposals.clear()
    assert proposals._proposals == {} and proposals.list_pending() == []   # approved is no longer pending


def test_propose_expense_tool_returns_pending_and_writes_nothing(shared_file):
    from app.ai import advisor_tools
    out = json.loads(advisor_tools.run_tool(
        "propose_expense", json.dumps({"amount": 4.2, "category": "Food", "description": "coffee"}), actor="alice"))
    assert out["status"] == "pending_approval"
    assert proposals.list_pending()[0].actor == "alice"


def test_propose_expense_tool_returns_a_constraint_error_as_data(shared_file):
    from app.ai import advisor_tools
    out = json.loads(advisor_tools.run_tool(
        "propose_expense", json.dumps({"amount": 9000, "category": "Food", "description": "x"})))
    assert "ProposalRejected" in out["error"] and "limit" in out["error"]


def test_review_cli_approves_with_the_typed_digest_and_executes(shared_file):
    from app.ai.labs import lab08_review
    p = _pending("alice")
    service = FakeService()
    service.load_expenses = lambda: None
    code = lab08_review.main(["approve", p.id, "--as", "bob"], ask=lambda _: p.digest, service=service)
    assert code == 0 and len(service.added) == 1


def test_review_cli_wrong_digest_is_denied(shared_file):
    from app.ai.labs import lab08_review
    p = _pending("alice")
    service = FakeService()
    service.load_expenses = lambda: None
    code = lab08_review.main(["approve", p.id, "--as", "bob"], ask=lambda _: "wrong", service=service)
    assert code == 1 and service.added == []


def test_path_is_read_from_the_environment_at_call_time(tmp_path, monkeypatch):
    # Regression: the env var is set AFTER proposals was imported (.env loads late); it must still work.
    monkeypatch.setenv("PROPOSALS_PATH", str(tmp_path / "late.json"))
    _pending()
    assert (tmp_path / "late.json").exists()
