"""Tests for the usage log and daily cap. No Azure."""
import json
import logging
from datetime import date, timedelta
from types import SimpleNamespace

import pytest

from app.ai import usage


@pytest.fixture(autouse=True)
def fresh_state(monkeypatch):
    monkeypatch.setitem(usage._state, "day", date.today())
    monkeypatch.setitem(usage._state, "tokens", 0)
    monkeypatch.setattr(usage, "DAILY_TOKEN_CAP", 1000)


def tokens(n_in, n_out):
    return SimpleNamespace(input_tokens=n_in, output_tokens=n_out)


def test_cost_is_exact_for_known_usage():
    # 1M in + 1M out on gpt-4.1-mini = 0.40 + 1.60 = 2.00 USD
    entry = usage.record("categorize", "dep", "gpt-4.1-mini-2025-04-14", tokens(1_000_000, 1_000_000), 0.5)
    assert entry["cost_usd"] == 2.0
    assert entry["price_known"] is True


def test_longest_matching_price_prefix_wins(monkeypatch):
    monkeypatch.setitem(usage.PRICES, "gpt-4o-mini", (0.15, 0.60))
    entry = usage.record("t", "d", "gpt-4o-mini-2024-07-18", tokens(1_000_000, 0), 0.1)
    assert entry["cost_usd"] == 0.15      # not the gpt-4o price


def test_unknown_model_is_flagged_not_priced():
    entry = usage.record("t", "d", "mystery-model", tokens(100, 100), 0.1)
    assert entry["cost_usd"] == 0.0
    assert entry["price_known"] is False


def test_cap_raises_once_tokens_reach_the_limit():
    usage.check_cap()                                  # fine at 0
    usage.record("t", "d", "gpt-4o", tokens(600, 400), 0.1)   # exactly 1000
    with pytest.raises(usage.DailyCapExceeded):
        usage.check_cap()


def test_counter_resets_on_a_new_day():
    usage.record("t", "d", "gpt-4o", tokens(600, 400), 0.1)
    usage._state["day"] = date.today() - timedelta(days=1)
    usage.check_cap()                                  # new day: no error
    assert usage._state["tokens"] == 0


def test_log_line_holds_numbers_only(caplog):
    with caplog.at_level(logging.INFO, logger="expense_ai.usage"):
        usage.record("categorize", "mini", "gpt-4.1-mini", tokens(10, 5), 0.25)
    data = json.loads(caplog.records[0].getMessage())
    assert set(data) == {"task", "deployment", "model", "in", "out",
                         "latency_s", "cost_usd", "price_known", "status"}


def test_record_response_tolerates_missing_usage():
    entry = usage.record_response("t", "dep", SimpleNamespace(), 0.1)
    assert entry["in"] == 0 and entry["out"] == 0 and entry["model"] == "dep"
