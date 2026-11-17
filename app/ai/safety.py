"""One place that interprets content-filter outcomes (Lab 7, D73-D74).

Field names come from the real probe output (lab07_probe): a blocked prompt is an
HTTP 400 BadRequestError with code "content_filter" and body["content_filters"];
a normal response carries a top-level `content_filters` list and `incomplete_details`.
"""
from dataclasses import dataclass, field
from enum import Enum

import openai


class Outcome(Enum):
    OK = "ok"
    PROMPT_BLOCKED = "prompt_blocked"          # rejected before the model ran
    RESPONSE_FILTERED = "response_filtered"    # cut or withheld after generation
    TRUNCATED = "truncated"                    # not safety: max_output_tokens


@dataclass
class SafeResult:
    outcome: Outcome
    text: str
    detail: dict = field(default_factory=dict)   # category/severity for LOGS ONLY (D74)


# Deliberately generic: no word "filter", "policy" or a category name (D74).
USER_MESSAGES = {
    Outcome.PROMPT_BLOCKED: "I can't help with that request. Please rephrase it.",
    Outcome.RESPONSE_FILTERED: "I can't share that answer. Please try a different question.",
    Outcome.TRUNCATED: "The answer was cut short. Please ask a narrower question.",
}


def _fired(content_filters) -> dict:
    """{category: severity or 'detected'} for every category that fired, for logs."""
    fired = {}
    for entry in content_filters or []:
        results = entry.get("content_filter_results", {}) if isinstance(entry, dict) else {}
        for category, verdict in results.items():
            if verdict.get("filtered"):
                fired[f"{entry.get('source_type', '?')}:{category}"] = verdict.get("severity", "detected")
    return fired


def interpret(call) -> SafeResult:
    """call() performs the model request and returns the response."""
    try:
        response = call()
    except openai.BadRequestError as error:
        if getattr(error, "code", None) == "content_filter":
            body = error.body if isinstance(error.body, dict) else {}
            entries = body.get("content_filters") or []
            blocked = {e.get("source_type") for e in entries if isinstance(e, dict) and e.get("blocked")}
            # Probe finding: a 400 can come from the COMPLETION side too. The prompt wins when
            # both fired; with no usable detail, assume the prompt (the common case).
            outcome = (Outcome.RESPONSE_FILTERED if blocked == {"completion"} else Outcome.PROMPT_BLOCKED)
            return SafeResult(outcome, USER_MESSAGES[outcome], {"fired": _fired(entries)})
        raise                                    # a real bug is not a safety event

    details = getattr(response, "incomplete_details", None)
    reason = getattr(details, "reason", None) if details else None
    filters = getattr(response, "content_filters", None)
    blocked_completion = any(
        isinstance(f, dict) and f.get("blocked") and f.get("source_type") == "completion"
        for f in filters or []
    )
    if reason == "content_filter" or blocked_completion:
        return SafeResult(Outcome.RESPONSE_FILTERED, USER_MESSAGES[Outcome.RESPONSE_FILTERED],
                          {"reason": reason, "fired": _fired(filters)})
    if reason == "max_output_tokens":
        return SafeResult(Outcome.TRUNCATED, response.output_text + " ...", {"reason": reason})
    return SafeResult(Outcome.OK, response.output_text, {})
