"""Tools the advisor agent can call. They run in OUR process, never in Azure."""
import json
import os

from azure.ai.projects.models import FunctionTool

from app.ai.retrieval import retrieve
from app.models import Category
from app.services.expense_service import ExpenseService
from app.storage import JsonExpenseStorage

EXPENSES_PATH = os.environ.get("EXPENSES_PATH", "expenses.json")


def get_spending_summary() -> dict:
    # Existing app code: deterministic totals, no LLM arithmetic (Lab 3 lesson).
    service = ExpenseService(JsonExpenseStorage(EXPENSES_PATH))
    service.load_expenses()
    summary = service.compute_summary()
    return {
        "total": round(summary.total, 2),
        "per_category": {c.value: round(v, 2) for c, v in summary.total_per_category.items()},
        "largest_expense": summary.largest_expense.to_dict() if summary.largest_expense else None,
    }


def search_expenses(query: str, category: str | None = None) -> list[dict]:
    # The model supplies the arguments, so validate them like any untrusted input.
    odata_filter = f"category eq '{Category(category).value}'" if category else None
    docs = retrieve(query, k=5, odata_filter=odata_filter)
    # Return only what the model needs: the raw result carries @search.* metadata
    # that costs input tokens on every turn and means nothing to the model.
    return [{k: d[k] for k in ("description", "category", "amount", "date")} for d in docs]


IMPLEMENTATIONS = {
    "get_spending_summary": get_spending_summary,
    "search_expenses": search_expenses,
}

TOOLS = [
    FunctionTool(
        name="get_spending_summary",
        description="Exact total spent, total per category and the largest expense. "
                    "Use for any question about totals, sums or comparisons.",
        parameters={"type": "object", "properties": {}, "required": [],
                    "additionalProperties": False},
        strict=True,
    ),
    FunctionTool(
        name="search_expenses",
        description="Find individual expense records by meaning or keyword. "
                    "Returns at most 5 records. Never use it to compute totals.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "What to look for"},
                "category": {"type": ["string", "null"],
                             "description": "Food, Transport, Entertainment, Utilities, Other, or null"},
            },
            "required": ["query", "category"],
            "additionalProperties": False,
        },
        strict=True,
    ),
]


def run_tool(name: str, arguments: str) -> str:
    # Errors go back to the model as data so it can recover or explain,
    # instead of crashing the conversation.
    try:
        result = IMPLEMENTATIONS[name](**json.loads(arguments))
    except Exception as err:
        result = {"error": f"{type(err).__name__}: {err}"}
    return json.dumps(result)