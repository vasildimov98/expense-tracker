import json
from unittest import result

import pytest

from app.ai import advisor_tools


@pytest.fixture
def expenses_file(tmp_path, monkeypatch):
    path = tmp_path / "expenses.json"
    path.write_text(json.dumps([
        {"category": "Food", "amount": 10.25, "description": "lunch", "date": "2026-10-01"},
        {"category": "Food", "amount": 5.5, "description": "coffee", "date": "2026-10-02"},
        {"category": "Transport", "amount": 20.0, "description": "taxi", "date": "2026-10-03"},
    ]))
    monkeypatch.setattr(advisor_tools, "EXPENSES_PATH", str(path))


def test_summary_totals_are_exact(expenses_file):
    result = advisor_tools.get_spending_summary()
    assert result["total"] == 35.75
    assert result["per_category"] == {"Food": 15.75, "Transport": 20.0}
    assert result["largest_expense"]["description"] == "taxi"


def test_search_returns_only_needed_fields(monkeypatch):
    raw = [{"id": "abc", "description": "x", "category": "Food", "amount": 1.0,
            "date": "2026-10-01", "@search.score": 0.1}]
    monkeypatch.setattr(advisor_tools, "retrieve", lambda query, k, odata_filter: raw)
    assert advisor_tools.search_expenses("x") == [
        {"description": "x", "category": "Food", "amount": 1.0, "date": "2026-10-01"}
    ]


def test_search_builds_filter_from_validated_category(monkeypatch):
    seen = {}

    def fake(query, k, odata_filter):
        seen["filter"] = odata_filter
        return []

    monkeypatch.setattr(advisor_tools, "retrieve", fake)
    advisor_tools.search_expenses("x", "Food")
    assert seen["filter"] == "category eq 'Food'"


def test_injected_category_is_rejected_before_searching(monkeypatch):
    monkeypatch.setattr(advisor_tools, "retrieve",
                        lambda *a, **k: pytest.fail("must not search"))
    evil = "Food' or amount gt 0 or category eq 'Food"
    out = json.loads(advisor_tools.run_tool(
        "search_expenses", json.dumps({"query": "x", "category": evil})))
    assert "error" in out


def test_unknown_tool_returns_error_json():
    out = json.loads(advisor_tools.run_tool("delete_expense", "{}"))
    assert "error" in out


def test_agent_has_no_write_tools():
    # D37 as a regression test: the agent may only read.
    names = [tool.name for tool in advisor_tools.TOOLS]
    assert not [n for n in names if n.startswith(("add", "delete", "update", "remove"))]