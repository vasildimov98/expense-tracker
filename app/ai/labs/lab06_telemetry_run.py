"""A small, varied workload with telemetry on: gives KQL something to query.

Costs cents: 12 tiny categorize calls, then 2 advisor-agent turns (tool calls).
"""
import openai

from app.ai import telemetry, usage
from app.ai.advisor_agent import chat
from app.ai.model_router import ask

telemetry.setup()
usage.enable_console("usage.jsonl")

try:
    for i in range(12):
        ask("categorize", "Reply with one word.", f"Categorize: coffee {i}", 20)

    try:
        response = chat("How much did I spend on food?")
        chat("And what about transport?", response.id)
    except openai.PermissionDeniedError as error:
        # Seen after the second-project experiment: the agent's Entra identity was disabled.
        print(f"\nAgent step skipped (403): {error}")
finally:
    telemetry.flush()   # always push what we have before the process exits

print("done: wait 2-5 minutes, then query Application Insights")
