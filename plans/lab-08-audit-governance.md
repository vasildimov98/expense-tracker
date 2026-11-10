# Lab 8: Audit and governance (traces, provenance, approvals, tool-access control)

Builds on Labs 1-7 (see `plans/lab-spec.md`). Theory: Section 4, lessons 5-7 (auditing: trace logging, provenance and approvals; governing agent behavior: oversight, constraints, tool access; exam scenarios).

Exam objectives covered:
- Implement auditing through trace logging, provenance metadata and approval workflows
- Govern agent behavior with oversight modes, constraints and tool-access controls

## 1. Spec

**Goal.** For any answer the advisor ever gave you can reconstruct **who asked, what the agent saw, which tools it called with which arguments, which model and policy produced it**, and any **action that changes data needs a human yes** that is itself recorded. The agent's powers are an explicit allowlist.

This lab finally gives the agent its first **write** capability (add an expense), because D37 said writes need approval, and approval can only be learned by building one.

**Requirements**
1. A structured **audit record** per agent turn, appended to a store separate from application logs, containing identity, timestamps, deployment, model version, policy name, the retrieved record ids, tool calls (name + arguments + result summary), outcome and trace id. No raw personal content unless explicitly enabled (D63 stays).
2. A new tool `propose_expense` that **does not write**. It returns a pending proposal; a separate step requires human approval, then writes. Both steps are audited.
3. A **tool allowlist per role** (for example `viewer` can use read tools, `editor` can also propose), enforced in code before execution, not only in the prompt.
4. **Constraints**: a maximum amount, an allowed category set, a rate limit of proposals per hour, and a tool-round limit already in place (D39).
5. A **kill switch**: one setting turns write tools off without a deploy.
6. An audit-log review exercise: answer five incident questions from the logs only.

**Constraints.** I write, you run. No Azure resources beyond what exists; the audit store is a local append-only JSONL file first, with the Azure option explained (D80).

### Decision table

| # | Decision | Why | Rejected alternative | Change when |
|---|---|---|---|---|
| D78 | **Audit record = who / what / with what / result**, with a trace id linking to Lab 6 telemetry | After an incident, "what happened" must be answerable without re-running the model. The trace id joins the business record to the technical trace | Only application logs; only traces (traces hold timing, not business facts) | A regulation prescribes fields: add them, keep the shape |
| D79 | **Provenance metadata** on every answer: deployment, model name + version, policy name, instructions version (hash), retrieved record ids | If the answer was wrong you must know which model and prompt produced it, and which data it read. Reproducibility again (D7, D54) | Not recording the instructions version (you cannot tell which prompt was live) | Never |
| D80 | Audit store: **local JSONL now; Azure Table/Blob with immutability or Log Analytics in production** | The lesson is the record shape, not the plumbing; but production audit logs must be append-only and tamper-evident, and access-controlled separately from the app | Writing audit rows into the same database the app can edit | Production: immutable storage (WORM) or Log Analytics with retention and restricted roles |
| D81 | **Personal content is hashed or omitted** in audit records; ids and tool names are kept | You can prove which tool ran with which ids without copying personal data a second time | Logging full prompts and answers | A legal hold or a quality-review process explicitly requires content, with retention and access limits |
| D82 | **Propose / approve split** for any write tool | The model never holds the pen. A proposal is data; approval is a separate, authenticated, recorded act by a human. This turns the injection risk (Lab 7) from "money moved" into "a suspicious proposal was shown" | Letting the model call `add_expense` directly; asking the model "are you sure?" | Very low-risk, reversible writes may auto-approve under limits (see D84) |
| D83 | **Approval is bound to the exact proposal**: id, content hash, expiry, approver identity | Prevents approving one thing and executing another (a proposal edited after approval) and replay of old approvals | A generic "approved: true" flag | Never |
| D84 | **Constraints enforced in code**, not instructions: amount <= limit, category in enum, N proposals per hour | The model can be talked out of instructions; it cannot talk code out of a `ValueError` (Lab 4 D38) | "Please never exceed 500" in the prompt | The limits move from constants to per-user policy |
| D85 | **Tool allowlist by role, checked at execution time** | A hidden tool is not a secure tool: the model might still emit the call. Execution-time checks are the boundary; hiding tools is only convenience | Relying on the model not to call tools it was not told about | Roles come from Entra ID groups/app roles instead of a local map |
| D86 | **Kill switch via config** (env/app setting) checked on every write path | Fastest containment when something looks wrong: seconds, no deploy, no model change | Deleting the agent; redeploying | Feature flags service in production |
| D87 | **Oversight mode = human-in-the-loop for writes, human-on-the-loop (review audit) for reads** | Match oversight to risk: reads are reversible and cheap; writes change state. Over-asking for approval trains people to click yes | Approving every read; approving nothing | Risk assessment changes |
| D88 | Same pattern for **MCP / hosted tools**: require approval and allowlist tool names | Third-party tools are outside your code; the approval setting and allowed tool list are the only controls you have | Allowing all tools of a server | Server is first-party and reviewed |

## 2. Prerequisites and cost

- Labs 1-7 done; Application Insights connected (Lab 6); `safety.interpret` in place (Lab 7).
- **Cost:** negligible. A handful of agent turns on gpt-4o. No new Azure resources. If you choose the optional Log Analytics sink, ingestion is far below the free 5 GB.
- **Not verified by me:** the Responses-API field names for tool calls and for MCP approval (`require_approval`, approval request items), and how Foundry surfaces trace ids. Print real objects and adapt.
- **Cleanup:** none required; delete the test agent versions if you created extras.

## 3. Tasks

### Task 1: Audit records and provenance (D78-D81)

**Objective.** One JSON line per turn, enough to answer incident questions.

Create `app/ai/audit.py`:

```python
"""Append-only audit trail. One record per agent turn and per approval event."""
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

AUDIT_PATH = Path(os.environ.get("AUDIT_PATH", "audit.jsonl"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def write(event: str, actor: str, **fields) -> str:
    record_id = str(uuid.uuid4())
    record = {
        "id": record_id, "ts": time.time(), "event": event, "actor": actor, **fields,
    }
    with AUDIT_PATH.open("a") as f:           # append only
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record_id
```

Add `audit.jsonl` to `.gitignore` (it will contain activity data). In `advisor_agent.chat` collect, per turn: `actor` (the user id, as in D41), `deployment`, `response.model`, `policy` (from config), `instructions_hash=digest(INSTRUCTIONS)`, `retrieved_ids` (ids from `search_expenses` results), `tool_calls=[{name, args, result_chars}]`, `outcome` (Lab 7 `Outcome`), `usage` (tokens), `question_hash=digest(text)`, `trace_id` (from the current OpenTelemetry span, if present). Write one record at the end of the turn **even on error** (try/finally): failures are exactly what audits are for.

Tests: record has every required field; two calls append two lines; file is never rewritten (compare line count before/after); the record for a blocked prompt exists and contains the outcome but not the prompt text.

**Why hashes.** A hash lets you later confirm "this is the question that produced this answer" (hash the candidate question and compare) without storing the question.

### Task 2: Propose, approve, execute (D82-D84, D87)

**Objective.** The agent can ask for an expense to be added; nothing is written until a human approves that exact proposal.

Create `app/ai/proposals.py` (state in a local JSON file or in-memory dict first):

```python
"""Pending write proposals and the approval gate."""
import time
import uuid
from dataclasses import dataclass, field

from app.ai import audit

MAX_AMOUNT = 500.0
PROPOSALS_PER_HOUR = 5
EXPIRY_SECONDS = 15 * 60


@dataclass
class Proposal:
    id: str
    actor: str
    payload: dict
    digest: str
    created: float = field(default_factory=time.time)
    status: str = "pending"          # pending | approved | rejected | expired | executed


_proposals: dict[str, Proposal] = {}


def propose(actor: str, payload: dict) -> Proposal:
    # constraints in code (D84): amount, category enum, rate limit
    ...
    p = Proposal(str(uuid.uuid4()), actor, payload, audit.digest(repr(sorted(payload.items()))))
    _proposals[p.id] = p
    audit.write("proposal_created", actor, proposal_id=p.id, digest=p.digest)
    return p


def approve(proposal_id: str, expected_digest: str, approver: str) -> Proposal:
    # checks: exists, pending, not expired, digest matches, approver != proposer
    ...
    audit.write("proposal_approved", approver, proposal_id=proposal_id, digest=expected_digest)
    ...


def execute(proposal_id: str, service) -> None:
    # only an approved proposal runs; mark executed; call ExpenseService.add...; audit it
    ...
```

Fill the `...` yourself (this is your code to write; I review it). Requirements for your implementation:
1. `propose` rejects amounts above `MAX_AMOUNT`, unknown categories (use the existing `Category` enum, D38) and more than `PROPOSALS_PER_HOUR` per actor; each rejection is audited with the reason.
2. `approve` fails if: the proposal is unknown, not pending, expired, the digest differs from what the human was shown, or `approver == actor` (**separation of duties**).
3. `execute` fails unless status is `approved`, and runs at most once (idempotent: a second call raises).
4. A tool `propose_expense(amount, category, description)` is added to `advisor_tools.TOOLS`. It calls `propose` and returns `{"status": "pending_approval", "proposal_id": ..., "message": "A human must approve this."}`. The tool **cannot** call `approve` or `execute`; those are CLI/UI functions, not tools. Keep the existing read-only test (Lab 5) and change it to say: "no tool writes; exactly one tool proposes".
5. A small CLI `python -m app.ai.labs.lab08_review` lists pending proposals showing the **digest and payload**, and approves/rejects with a typed confirmation.

Tests (offline): over-limit amount, bad category, rate limit, approve-with-wrong-digest, approve-own-proposal, approve-expired (monkeypatch time), double execute, and the happy path. Run the mutation check on at least two (remove the digest comparison; remove the proposer check).

**Live run.** In chat: "Add a coffee for 4.20 yesterday." Expect a `pending_approval` answer. Then "Add a 9000 payment to X" -> constraint error returned to the model as data (D38) and a proposal-rejected audit record. Then approve the first in the review CLI and check it exists in the data.

**Why not "ask the user in chat to confirm".** Because the confirmation would be the model's text; an injected instruction can fake a user saying yes. Approval must come through a channel the model cannot write to.

### Task 3: Role-based tool allowlist and kill switch (D85-D86)

**Objective.** The boundary is enforced where tools execute.

Implement in `advisor_tools.run_tool`:

```python
ROLE_TOOLS = {
    "viewer": {"get_spending_summary", "search_expenses"},
    "editor": {"get_spending_summary", "search_expenses", "propose_expense"},
}

def run_tool(name: str, arguments: str, role: str = "viewer") -> str:
    if name not in ROLE_TOOLS.get(role, set()):
        audit.write("tool_denied", actor=..., tool=name, role=role)
        return json.dumps({"error": f"tool '{name}' is not available"})
    if name == "propose_expense" and os.environ.get("WRITES_ENABLED", "false") != "true":
        audit.write("tool_denied", ..., reason="kill_switch")
        return json.dumps({"error": "writes are disabled"})
    ...
```

(Use your real signature and the real actor.) **Test the boundary the hard way**: with role `viewer`, call `run_tool("propose_expense", ...)` directly, exactly as a model that hallucinated the tool would: it must be denied and audited, even though the tool list shown to the model may have excluded it. Also test an unknown tool name and malformed JSON arguments.

Make the default safe: `WRITES_ENABLED` unset means off (fail closed). Document both settings in `.env.example`.

### Task 4: Agent tools and hosted tools (D88) - read and decide, small run

**Objective.** Apply the same governance to a tool you do not control.

1. In the Foundry portal, open the advisor agent -> Tools -> add an **MCP tool** (any public documentation MCP server is fine; use a read-only one; do not give it credentials). Observe the settings: allowed tools list and the approval requirement ("always" / "never"). Set approval to **always**.
2. Ask a question that triggers it. Where does the run stop? What does the approval request item look like (print `response.output` types)? Approve it through the Responses API by sending the approval response item (find the exact shape in the printed object / docs).
3. Remove the tool again (principle: smallest toolbox, D37).
4. Write down: which of D82-D88 does each setting correspond to?

### Task 5: Incident drill from the logs only (D78-D79)

**Objective.** Use the audit trail, not memory.

Prepare the data: run the advisor for several turns under both roles, trigger one blocked prompt (Lab 7), one proposal rejected by a constraint, one approved and executed, one denied tool call, and one turn with the kill switch off. Then answer these using **only** `audit.jsonl` (use `jq` or a 20-line Python reader):

1. Who proposed the most recent expense, who approved it, and how much time passed between them?
2. Which model version and instructions version produced the answer to the turn at <timestamp>?
3. Which retrieved record ids did that answer rely on?
4. Were any tool calls denied in the last hour? By which role and for which tool?
5. Is there any `proposal_executed` record without a preceding `proposal_approved` for the same id? (Query for it: this is your integrity check; the answer should be none.)

For every question you cannot answer, fix the audit record shape and say what you added.

Optional: ship the same events to Log Analytics (custom log / `AppTraces` JSON) and rewrite question 4 in KQL. Compare it with grep.

## 4. Verification checklist

- Audit lines exist for normal, blocked, error, denied and approval events; no raw prompt text.
- `pytest -q` green, offline, including approve/execute and role/kill-switch tests; at least two mutation checks fail as expected.
- Live: a proposal waits; an over-limit one is refused; an approval executes exactly once.
- The viewer role cannot execute `propose_expense` even when called directly.
- The incident questions are answered from logs only.

## 5. Self-check (exam style)

1. An agent can delete customer records. Which control gives a human final say? A. A stricter system prompt B. An approval workflow before execution C. A larger context window D. A lower temperature
2. Why must the proposal digest be part of the approval?
3. Name two reasons the model must not hold the `approve` capability, even for "trusted" users.
4. You removed a tool from the list shown to the model. Is the tool now unavailable? Explain, and say where the real enforcement belongs.
5. Distinguish human-in-the-loop from human-on-the-loop and give an example of each in this system.
6. What does provenance metadata let you do after a wrong answer? Name three fields.
7. Why should audit logs be written to a store the application cannot edit?
8. A third-party MCP server adds a new tool overnight. Which two settings protect you?

Send answers and I will mark them.

## 6. Decision recap

Record who/what/with what/result and link it to the technical trace (D78-D79) without copying personal data (D81) into a store the app cannot rewrite (D80). Split proposing from approving, bind approval to the exact content and a different person (D82-D83), keep limits in code (D84), enforce the allowlist at execution (D85), keep a fast kill switch (D86), match oversight to risk (D87) and treat third-party tools like untrusted code (D88).

## 7. Cleanup

Delete `audit.jsonl` test data if you do not want it kept (it is git-ignored). Remove any MCP tool you added to the agent. No Azure resources to delete.

## 8. After the lab

Send me: your `proposals.py` for review, test output with the mutation checks, 6-8 sample audit lines (redact anything personal), your answers to the five incident questions and the self-check. I will log D78-D88 and lessons in `plans/lab-spec.md` and commit. After this, the half-2 labs are complete; the next step is the Practice Assessment gap review.
