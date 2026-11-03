import json
import os
import time
from pathlib import Path

from app.ai.foundry_client import get_openai_client
from app.models import Category

CATEGORIES = [c.value for c in Category]

INSTRUCTIONS = (
    "You categorize personal expenses. "
    f"Answer with exactly one of: {', '.join(CATEGORIES)}. No other text. If an expense has several parts, choose the category of the largest or primary purpose."
)

# USD per 1M tokens: (input, output). From the Azure Retail Prices API, swedencentral.
PRICES = {
    os.environ["FOUNDRY_MODEL_DEPLOYMENT"]: (0.40, 1.60),    # gpt-4.1-mini
    os.environ["FOUNDRY_ADVISOR_DEPLOYMENT"]: (3.025, 12.10),  # gpt-4o, Standard (regional)
}

client = get_openai_client()
items = json.loads((Path(__file__).parent / "lab02_eval_set.json").read_text())


def evaluate(deployment: str) -> dict:
    correct = in_tok = out_tok = 0
    latencies = []
    for item in items:
        start = time.perf_counter()
        response = client.responses.create(
            model=deployment,
            instructions=INSTRUCTIONS,
            input=item["description"],
            max_output_tokens=16,
        )
        latencies.append(time.perf_counter() - start)
        in_tok += response.usage.input_tokens
        out_tok += response.usage.output_tokens
        answer = response.output_text.strip()
        ok = answer == item["label"]
        correct += ok
        if not ok:
            print(f"  [{deployment}] '{item['description']}' -> {answer} (expected {item['label']})")
    price_in, price_out = PRICES[deployment]
    return {
        "deployment": deployment,
        "accuracy": f"{correct}/{len(items)}",
        "avg_latency_s": round(sum(latencies) / len(latencies), 2),
        "tokens": in_tok + out_tok,
        "cost_usd": round((in_tok * price_in + out_tok * price_out) / 1_000_000, 6),
    }


for dep in PRICES:
    print(evaluate(dep))