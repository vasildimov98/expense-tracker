"""The Expense Advisor agent: definition in Foundry, tools executed locally."""
import time
from functools import lru_cache

from azure.ai.projects.models import PromptAgentDefinition

from app.ai import usage
from app.ai.advisor_tools import TOOLS, run_tool
from app.ai.foundry_client import get_project_client
from app.ai.model_router import deployment_for

AGENT_NAME = "expense-advisor"
MAX_TOOL_ROUNDS = 5   # guard against a runaway tool loop (cost)

INSTRUCTIONS = (
    "You are a concise personal-finance advisor for the user's own expenses. "
    "For totals, sums and comparisons ALWAYS call get_spending_summary: never add numbers yourself. "
    "Use search_expenses to look up individual records. "
    "Answer only from tool results; if they do not contain the answer, say so. "
    "You can only read data, you cannot change it."
)


def create_agent():
    # Each call creates a new VERSION of the same named agent.
    return get_project_client().agents.create_version(
        agent_name=AGENT_NAME,
        definition=PromptAgentDefinition(
            model=deployment_for("advise"),   # deployment NAME, again
            instructions=INSTRUCTIONS,
            tools=TOOLS,
        ),
    )


@lru_cache(maxsize=1)
def _client():
    return get_project_client().get_openai_client()


def chat(text: str, previous_response_id: str | None = None):
    """One user turn. Returns the final response; pass its .id into the next turn."""
    agent = {"extra_body": {"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
             "max_output_tokens": 500}
    kwargs = {"previous_response_id": previous_response_id} if previous_response_id else {}

    def create(**call_kwargs):
        usage.check_cap()   # every round can cost tokens, so check every round
        started = time.monotonic()
        result = _client().responses.create(**call_kwargs)
        usage.record_response("advise", AGENT_NAME, result, time.monotonic() - started)
        return result

    response = create(input=text, **agent, **kwargs)
    for _ in range(MAX_TOOL_ROUNDS):
        calls = [item for item in response.output if item.type == "function_call"]
        if not calls:
            return response
        outputs = [
            {"type": "function_call_output", "call_id": c.call_id,
             "output": run_tool(c.name, c.arguments)}
            for c in calls
        ]
        response = create(input=outputs, previous_response_id=response.id, **agent)
    raise RuntimeError(f"No final answer after {MAX_TOOL_ROUNDS} tool rounds")