"""Fire concurrent requests at the capacity-10 deployment and count outcomes."""
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import openai

from app.ai.foundry_client import get_openai_client
from app.ai.model_router import deployment_for

client = get_openai_client().with_options(max_retries=0)   # see the raw 429s


def one(i: int) -> str:
    try:
        client.responses.create(
            model=deployment_for("categorize"),
            input=f"Categorize: coffee {i}",
            max_output_tokens=20,
        )
        return "ok"
    except openai.RateLimitError as e:
        retry_after = e.response.headers.get("retry-after", "none")
        return f"429 (retry-after={retry_after})"


start = time.time()
with ThreadPoolExecutor(max_workers=30) as pool:
    results = Counter(pool.map(one, range(120)))
print(results, f"in {time.time() - start:.1f}s")
