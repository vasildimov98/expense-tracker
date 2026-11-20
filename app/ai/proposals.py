"""Pending write proposals and the approval gate (Lab 8, D82-D84).

The model may only PROPOSE. Approving and executing are human/code steps that are
deliberately not exposed as tools.
"""
import json
import os
import time
import uuid
from dataclasses import asdict, dataclass, field
from pathlib import Path

from app.ai import audit
from app.models import Category

MAX_AMOUNT = 500.0
PROPOSALS_PER_HOUR = 5
EXPIRY_SECONDS = 15 * 60
RATE_WINDOW_SECONDS = 60 * 60


class ProposalRejected(Exception):
    """A constraint said no. The message is safe to show the model: it is data, not a crash (D38)."""


@dataclass
class Proposal:
    id: str
    actor: str
    payload: dict
    digest: str
    created: float = field(default_factory=time.time)
    status: str = "pending"          # pending | approved | rejected | expired | executed


_proposals: dict[str, Proposal] = {}

# The chat and the review CLI are different processes, so they must share state through a file.
# Unset (the default, and in tests) = memory only.
PROPOSALS_PATH: str | None = None     # explicit override (tests); normally the env var is used


def _path() -> str | None:
    # Read at CALL time, not import time: .env is loaded as a side effect of importing foundry_client,
    # and depending on import order that can happen after this module was imported.
    return PROPOSALS_PATH or os.environ.get("PROPOSALS_PATH") or None


def _load() -> None:
    path = _path()
    if not path or not Path(path).exists():
        return
    raw = json.loads(Path(path).read_text())
    _proposals.clear()
    _proposals.update({pid: Proposal(**fields) for pid, fields in raw.items()})


def _save() -> None:
    path = _path()
    if not path:
        return
    tmp = Path(path + ".tmp")
    tmp.write_text(json.dumps({pid: asdict(p) for pid, p in _proposals.items()}, indent=2))
    os.replace(tmp, path)        # atomic: a reader never sees a half-written file


def list_pending() -> list[Proposal]:
    _load()
    return [p for p in _proposals.values() if p.status == "pending"]


def _now() -> float:
    return time.time()               # one seam, so tests can move the clock


def payload_digest(payload: dict) -> str:
    # Canonical form: sorted keys, so the same content always gives the same digest.
    return audit.digest(repr(sorted(payload.items())))


def _reject(actor: str, payload: dict, reason: str) -> None:
    # Audit the refusal WITH the reason, and a hash of the payload, never the payload (D81).
    audit.write("proposal_rejected", actor, reason=reason, payload_hash=payload_digest(payload))
    raise ProposalRejected(reason)


def propose(actor: str, payload: dict) -> Proposal:
    """Validate against the constraints in code (D84), then store a PENDING proposal. Writes nothing."""
    _load()
    amount = payload.get("amount")
    if isinstance(amount, bool) or not isinstance(amount, (int, float)) or amount <= 0:
        _reject(actor, payload, "amount must be a positive number")
    if amount > MAX_AMOUNT:
        _reject(actor, payload, f"amount exceeds the limit of {MAX_AMOUNT:g}")
    try:
        Category(payload.get("category"))            # the enum IS the allowlist (D38)
    except ValueError:
        allowed = ", ".join(c.value for c in Category)
        _reject(actor, payload, f"category must be one of: {allowed}")

    # Sliding window: only this actor's proposals from the last hour count.
    cutoff = _now() - RATE_WINDOW_SECONDS
    recent = [p for p in _proposals.values() if p.actor == actor and p.created > cutoff]
    if len(recent) >= PROPOSALS_PER_HOUR:
        _reject(actor, payload, f"rate limit: {PROPOSALS_PER_HOUR} proposals per hour")

    proposal = Proposal(str(uuid.uuid4()), actor, payload, payload_digest(payload), created=_now())
    _proposals[proposal.id] = proposal
    _save()
    audit.write("proposal_created", actor, proposal_id=proposal.id, digest=proposal.digest)
    return proposal


class ApprovalError(Exception):
    """approve/reject/execute refused. Raised to the human-facing caller (CLI), never to the model."""


def _deny(event: str, actor: str, proposal_id: str, reason: str) -> None:
    audit.write(event, actor, proposal_id=proposal_id, reason=reason)
    raise ApprovalError(reason)


def approve(proposal_id: str, expected_digest: str, approver: str) -> Proposal:
    """A human says yes to THIS content. expected_digest is what they were shown (D83)."""
    _load()
    p = _proposals.get(proposal_id)
    if p is None:
        _deny("approval_denied", approver, proposal_id, "unknown proposal")
    if p.status != "pending":
        _deny("approval_denied", approver, proposal_id, f"proposal is {p.status}, not pending")
    if _now() - p.created > EXPIRY_SECONDS:
        p.status = "expired"
        _save()
        _deny("approval_denied", approver, proposal_id, "proposal expired")
    if expected_digest != p.digest:          # the human saw something else than what is stored
        _deny("approval_denied", approver, proposal_id, "digest mismatch")
    if approver == p.actor:                  # separation of duties
        _deny("approval_denied", approver, proposal_id, "approver cannot be the proposer")
    p.status = "approved"
    _save()
    audit.write("proposal_approved", approver, proposal_id=proposal_id, digest=p.digest,
                proposer=p.actor, seconds_since_proposal=round(_now() - p.created, 1))
    return p


def reject(proposal_id: str, approver: str) -> Proposal:
    _load()
    p = _proposals.get(proposal_id)
    if p is None or p.status != "pending":
        _deny("rejection_denied", approver, proposal_id, "unknown or not pending")
    p.status = "rejected"
    _save()
    audit.write("proposal_rejected_by_human", approver, proposal_id=proposal_id, digest=p.digest)
    return p


def execute(proposal_id: str, service, executor: str = "system") -> None:
    """Run an APPROVED proposal exactly once. `service` is the ExpenseService (the only writer)."""
    _load()
    p = _proposals.get(proposal_id)
    if p is None:
        _deny("execution_denied", executor, proposal_id, "unknown proposal")
    if p.status != "approved":
        _deny("execution_denied", executor, proposal_id, f"proposal is {p.status}, not approved")
    if payload_digest(p.payload) != p.digest:    # edited after approval: approval no longer applies
        _deny("execution_denied", executor, proposal_id, "payload changed after approval")
    p.status = "executed"                        # flip BEFORE writing: a second call must fail, even mid-write
    _save()
    try:
        service.add_expense(Category(p.payload["category"]), p.payload["amount"], p.payload["description"])
    except Exception as err:
        p.status = "approved"                    # add_expense rolled back, so a retry is safe
        _save()
        audit.write("proposal_execute_failed", executor, proposal_id=proposal_id, error=type(err).__name__)
        raise
    audit.write("proposal_executed", executor, proposal_id=proposal_id, digest=p.digest)
