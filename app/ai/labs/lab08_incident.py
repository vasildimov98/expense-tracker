"""Lab 8, Task 5: answer incident questions from audit.jsonl ONLY (no model, no memory).

    python -m app.ai.labs.lab08_incident [--turn-ts 1795185902] [--hours 1]

Q1 last executed expense: proposer, approver, time between      Q4 denied tool calls in the last N hours
Q2/Q3 model + instructions version and retrieved ids of a turn   Q5 integrity: executed without approval
Reads a snapshot of the file, never writes it.
"""
import argparse
import json
import time
from pathlib import Path

from app.ai import audit


def read_records(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]


def _first(records, event, proposal_id):
    return next((r for r in records if r["event"] == event and r.get("proposal_id") == proposal_id), None)


def last_executed_chain(records: list[dict]) -> dict | None:
    """Q1: who proposed the most recent executed expense, who approved it, and how long it took."""
    executed = [r for r in records if r["event"] == "proposal_executed"]
    if not executed:
        return None
    last = max(executed, key=lambda r: r["ts"])
    created = _first(records, "proposal_created", last["proposal_id"])
    approved = _first(records, "proposal_approved", last["proposal_id"])
    return {
        "proposal_id": last["proposal_id"],
        "proposer": created["actor"] if created else None,
        "approver": approved["actor"] if approved else None,
        "seconds_proposal_to_approval": round(approved["ts"] - created["ts"], 1) if created and approved else None,
        "seconds_approval_to_execution": round(last["ts"] - approved["ts"], 1) if approved else None,
    }


def turn_at(records: list[dict], ts: float | None) -> dict | None:
    """Q2 + Q3: the agent turn at (the latest at or before) ts. None means the latest turn."""
    turns = [r for r in records if r["event"] == "agent_turn" and (ts is None or r["ts"] <= ts)]
    if not turns:
        return None
    t = max(turns, key=lambda r: r["ts"])
    return {k: t.get(k) for k in ("ts", "actor", "role", "deployment", "model", "model_version",
                                  "instructions_hash", "policy", "retrieved_ids", "trace_id")}


def denied_since(records: list[dict], seconds: float, now: float | None = None) -> list[dict]:
    """Q4: tool_denied events in the last `seconds`, with role, tool and reason."""
    cutoff = (now if now is not None else time.time()) - seconds
    return [{k: r.get(k) for k in ("ts", "actor", "role", "tool", "reason")}
            for r in records if r["event"] == "tool_denied" and r["ts"] >= cutoff]


def integrity_violations(records: list[dict]) -> list[dict]:
    """Q5: an executed proposal with no EARLIER approval for the same id, or executed twice."""
    problems = []
    seen_executed = set()
    for r in sorted((r for r in records if r["event"] == "proposal_executed"), key=lambda r: r["ts"]):
        pid = r["proposal_id"]
        approved = _first(records, "proposal_approved", pid)
        if approved is None or approved["ts"] > r["ts"]:
            problems.append({"proposal_id": pid, "problem": "executed without a preceding approval"})
        if pid in seen_executed:
            problems.append({"proposal_id": pid, "problem": "executed more than once"})
        seen_executed.add(pid)
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(prog="lab08_incident")
    parser.add_argument("--turn-ts", type=float, default=None, help="timestamp for Q2/Q3 (default: latest turn)")
    parser.add_argument("--hours", type=float, default=1.0, help="window for Q4")
    args = parser.parse_args(argv)
    records = read_records(audit.AUDIT_PATH)
    print(f"{len(records)} records in {audit.AUDIT_PATH}\n")
    print("Q1 last executed expense :", json.dumps(last_executed_chain(records), indent=2))
    print("Q2/Q3 turn               :", json.dumps(turn_at(records, args.turn_ts), indent=2))
    print(f"Q4 denied, last {args.hours:g} h     :", json.dumps(denied_since(records, args.hours * 3600), indent=2))
    problems = integrity_violations(records)
    print("Q5 integrity violations  :", json.dumps(problems, indent=2) if problems else "none")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
