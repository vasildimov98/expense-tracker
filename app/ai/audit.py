"""Append-only audit trail. One record per agent turn and per approval event."""
import hashlib
import json
import os
import time
import uuid
from pathlib import Path

from opentelemetry import trace

AUDIT_PATH = Path(os.environ.get("AUDIT_PATH", "audit.jsonl"))


def digest(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()[:16]


def current_trace_id() -> str | None:
    """Trace id of the active span as 32 hex chars (joins this record to the Lab 6 trace).

    None when no real span is active (telemetry off): an invalid context has trace_id 0.
    """
    context = trace.get_current_span().get_span_context()
    return format(context.trace_id, "032x") if context.is_valid else None


def write(event: str, actor: str, **fields) -> str:
    record_id = str(uuid.uuid4())
    record = {
        "id": record_id, "ts": time.time(), "event": event, "actor": actor, **fields,
    }
    with AUDIT_PATH.open("a") as f:           # append only
        f.write(json.dumps(record, sort_keys=True) + "\n")
    return record_id