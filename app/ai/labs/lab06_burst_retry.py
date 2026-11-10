"""Same burst as lab06_burst, but through model_router.ask (retry + failover)."""
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import openai

from app.ai import usage
from app.ai.model_router import ask

usage.enable_console("usage.jsonl")   # one JSON line per successful call


def one(i: int) -> str:
    try:
        ask("categorize", "Reply with one word.", f"Categorize: coffee {i}", 20)
        return "ok"
    except openai.RateLimitError:
        return "429 (gave up)"
    except openai.APITimeoutError:
        return "timeout (gave up)"


start = time.time()
with ThreadPoolExecutor(max_workers=30) as pool:
    results = Counter(pool.map(one, range(30)))
print(results, f"in {time.time() - start:.1f}s")
