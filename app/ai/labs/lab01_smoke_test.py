from app.ai.foundry_client import get_openai_client, DEPLOYMENT

client = get_openai_client()

response = client.responses.create(
    model=DEPLOYMENT,              # the deployment NAME, not the model name
    instructions="You are a concise financial assistant.",  # system-level behavior
    input="Categorize this expense in one word: 'Starbucks latte 4.50'",
    max_output_tokens=50,          # a hard cap on output size (and cost)
)

print("Answer:", response.output_text)
print("Tokens used:", response.usage.total_tokens)