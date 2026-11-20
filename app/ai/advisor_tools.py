"""Tools the advisor agent can call. They run in OUR process, never in Azure."""
import json
import os
from contextvars import ContextVar

from azure.ai.projects.models import FunctionTool

from app.ai import proposals
from app.ai.retrieval import retrieve
from app.models import Category
from app.services.expense_service import ExpenseService
from app.storage import JsonExpenseStorage

EXPENSES_PATH = os.environ.get("EXPENSES_PATH", "expenses.json")


# Audit side channel (D79): the caller sets a list, search_expenses appends the ids of the records
# it read. The MODEL never sees ids (they cost tokens and mean nothing to it); the audit trail does.
RETRIEVED_IDS: ContextVar[list | None] = ContextVar("retrieved_ids", default=None)


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
    seen = RETRIEVED_IDS.get()
    if seen is not None:
        seen.extend(d["id"] for d in docs if "id" in d)
    # Return only what the model needs: the raw result carries @search.* metadata
    # that costs input tokens on every turn and means nothing to the model.
    return [{k: d[k] for k in ("description", "category", "amount", "date")} for d in docs]


def propose_expense(amount: float, category: str, description: str, *, actor: str) -> dict:
    # PROPOSES only (D82): nothing is written. `actor` is keyword-only and injected by run_tool,
    # so the model can never choose who it is acting as.
    p = proposals.propose(actor, {"amount": amount, "category": category, "description": description})
    return {"status": "pending_approval", "proposal_id": p.id, "message": "A human must approve this."}


IMPLEMENTATIONS = {
    "get_spending_summary": get_spending_summary,
    "search_expenses": search_expenses,
    "propose_expense": propose_expense,
}

# Tools that need the caller's identity. It comes from trusted code, never from model arguments.
ACTOR_TOOLS = {"propose_expense"}

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
    FunctionTool(
        name="propose_expense",
        description="Ask to ADD one expense. This does not add it: it creates a request that a human "
                    "must approve. Never tell the user the expense was added.",
        parameters={
            "type": "object",
            "properties": {
                "amount": {"type": "number", "description": "Positive amount"},
                "category": {"type": "string", "enum": [c.value for c in Category]},
                "description": {"type": "string", "description": "Short description"},
            },
            "required": ["amount", "category", "description"],
            "additionalProperties": False,
        },
        strict=True,
    ),
]


def spotlight(text: str) -> str:
    """Mark retrieved text as data (Lab 7, D70/D72). Mode comes from the SPOTLIGHT env var, read per call:

    none (default): untrusted text goes in as-is; the indirect-attack shield cannot tell it is a document.
    mark: wrap in triple quotes, the delimiter Prompt Shields uses to recognise documents.
    full: mark + <<DATA>> tags the instructions refer to (the model-side layer).
    """
    mode = os.environ.get("SPOTLIGHT", "none")
    if mode == "mark":
        return f'"""{text}"""'
    if mode == "full":
        return f'<<DATA>>"""{text}"""<</DATA>>'
    return text


# Only tools that return text from the data store are untrusted. Local computed totals are not.
UNTRUSTED_TOOLS = {"search_expenses"}


def run_tool(name: str, arguments: str, actor: str = "local-user") -> str:
    # Errors go back to the model as data so it can recover or explain,
    # instead of crashing the conversation.
    try:
        kwargs = json.loads(arguments)
        if name in ACTOR_TOOLS:
            kwargs["actor"] = actor          # overwrite: a model-supplied "actor" is ignored
        result = IMPLEMENTATIONS[name](**kwargs)
    except Exception as err:
        result = {"error": f"{type(err).__name__}: {err}"}
    output = json.dumps(result)
    return spotlight(output) if name in UNTRUSTED_TOOLS else output