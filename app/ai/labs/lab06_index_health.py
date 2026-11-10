"""Index health (Lab 6, Task 4, D64): count parity + golden queries (hit@k).

Run from the project root:  python -m app.ai.labs.lab06_index_health
Exit code 0 = healthy, 1 = something is wrong (usable in a pipeline later).
"""
import json
import os
import sys
from pathlib import Path

K = 5
DEFAULT_SOURCE = Path(__file__).parent / "lab03_seed_expenses.json"

# (query, description of the expense that MUST appear in the top K).
# Matched by description, not by id: ids are hashes of the whole record (D29),
# so an id would break whenever an amount or date in the seed is edited.
GOLDEN = [
    ("coffee", "Starbucks latte"),                      # semantic: coffee != latte as words
    ("supermarket groceries", "Lidl weekly groceries"),
    ("monthly streaming subscription", "Netflix subscription"),
]


def count_ok(source_count: int, index_count: int) -> bool:
    return source_count == index_count


def golden_hits(results_by_query: dict[str, list[str]]) -> list[tuple[str, str, bool]]:
    """Pure check: for each golden pair, is the expected description in the top K?"""
    return [
        (query, expected, expected in results_by_query.get(query, []))
        for query, expected in GOLDEN
    ]


def main() -> int:
    # Imported here so the pure functions above can be tested without Azure env vars.
    from app.ai.retrieval import retrieve
    from app.ai.search_client import INDEX_NAME, get_index_client, get_search_client

    source = json.loads(Path(os.environ.get("EXPENSES_PATH", DEFAULT_SOURCE)).read_text())
    stats = get_index_client().get_index_statistics(INDEX_NAME)
    # Live count query. stats.document_count is a periodically refreshed summary
    # and lags minutes behind uploads/deletes (seen in Lab 6), so it can't be trusted here.
    index_count = get_search_client().get_document_count()
    ok = True

    print(f"source={len(source)} index={index_count} storage={stats.storage_size}B")
    if not count_ok(len(source), index_count):
        print("FAIL: count mismatch (dropped or duplicated documents)")
        ok = False

    results = {
        query: [d["description"] for d in retrieve(query, k=K)]
        for query, _ in GOLDEN
    }
    hits = 0
    for query, expected, found in golden_hits(results):
        hits += found
        print("PASS" if found else "FAIL", f"{query!r} -> expects {expected!r}; got {results[query]}")
    print(f"hit@{K}: {hits}/{len(GOLDEN)}")

    return 0 if ok and hits == len(GOLDEN) else 1


if __name__ == "__main__":
    sys.exit(main())
