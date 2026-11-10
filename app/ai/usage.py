"""Per-call usage log and a daily token cap (Lab 6, Task 2).

Why in our own code: the portal shows totals per deployment, not per task,
and this subscription has no budget alerts (D14). Numbers only, never prompt
or answer text (D63: expense data is personal data).
"""
import json
import logging
import threading
from datetime import date

log = logging.getLogger("expense_ai.usage")

# USD per 1M tokens (input, output), from the Azure Retail Prices API (D21).
# Re-check before relying on them. Matched by prefix of response.model.
PRICES = {
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o": (3.025, 12.10),
}
DAILY_TOKEN_CAP = 200_000

_lock = threading.Lock()
_state = {"day": date.today(), "tokens": 0}


class DailyCapExceeded(RuntimeError):
    pass


def check_cap() -> None:
    """Call BEFORE a model call. Fails closed when today's budget is spent."""
    with _lock:
        _roll_day()
        if _state["tokens"] >= DAILY_TOKEN_CAP:
            raise DailyCapExceeded(
                f"{_state['tokens']} tokens used today (cap {DAILY_TOKEN_CAP})"
            )


def _roll_day() -> None:
    if _state["day"] != date.today():
        _state.update(day=date.today(), tokens=0)


def _price_for(model: str) -> tuple[float, float] | None:
    matches = [name for name in PRICES if model.startswith(name)]
    return PRICES[max(matches, key=len)] if matches else None


def record(task: str, deployment: str, model: str, usage, latency_s: float,
           status: str = "completed") -> dict:
    """Call AFTER a model call. Counts tokens toward the cap and logs one JSON line."""
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    price = _price_for(model)
    cost = ((tokens_in * price[0] + tokens_out * price[1]) / 1e6) if price else 0.0
    with _lock:
        _roll_day()
        _state["tokens"] += tokens_in + tokens_out
    entry = {
        "task": task, "deployment": deployment, "model": model,
        "in": tokens_in, "out": tokens_out,
        "latency_s": round(latency_s, 3),
        "cost_usd": round(cost, 6), "price_known": price is not None,
        "status": status,
    }
    log.info(json.dumps(entry))
    return entry


def record_response(task: str, deployment: str, response, latency_s: float) -> dict:
    """record() for a Responses API object; tolerant of missing fields."""
    return record(
        task, deployment,
        model=getattr(response, "model", None) or deployment,
        usage=getattr(response, "usage", None),
        latency_s=latency_s,
        status=getattr(response, "status", None) or "completed",
    )


def enable_console(path: str | None = None) -> None:
    """For lab scripts: show our log lines (and optionally append to a file).

    Only our own logger is touched, so SDK and HTTP libraries stay quiet.
    """
    log.setLevel(logging.INFO)
    log.propagate = False
    handlers = [logging.StreamHandler()]
    if path:
        handlers.append(logging.FileHandler(path))
    for handler in handlers:
        handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(handler)
