from app.ai import usage
from app.ai.advisor_agent import chat, create_agent

usage.enable_console("usage.jsonl")

agent = create_agent()
print(f"Agent {agent.name} version {agent.version}\n")

previous = None
for question in [
    "How much did I spend on food?",
    "And what about transport?",          # needs memory of the previous turn
    "Which single expense was the largest?",
    "How much did I spend in Japan?",
    "What did I spend at Corner Cafe Lumen?"
]:
    response = chat(question, previous)
    previous = response.id
    print(f"Q: {question}\nA: {response.output_text}\n")