from app.ai import usage
from app.ai.model_router import ask, deployment_for

usage.enable_console("usage.jsonl")

print(deployment_for("categorize"), deployment_for("advise"))
print(ask("categorize", "Answer with one word: the expense category.", "Lidl groceries", 16))
print(ask("advise", "You are a concise financial advisor.",
          "I spend 40% of income on food. Is that high? Two sentences.", 120))