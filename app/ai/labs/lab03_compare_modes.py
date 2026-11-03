from azure.search.documents.models import VectorizedQuery

from app.ai.foundry_client import get_embeddings_client
from app.ai.search_client import EMBEDDING_DEPLOYMENT, get_search_client

K = 5
client = get_search_client()


def embed(text: str) -> list[float]:
    return get_embeddings_client().embeddings.create(
        model=EMBEDDING_DEPLOYMENT, input=text
    ).data[0].embedding


def run(query: str, mode: str, odata_filter: str | None = None) -> list[str]:
    # The only difference between the modes is which halves we pass.
    search_text = query if mode in ("keyword", "hybrid") else None
    vector_queries = (
        [VectorizedQuery(vector=embed(query), k_nearest_neighbors=K, fields="content_vector")]
        if mode in ("vector", "hybrid")
        else None
    )
    results = client.search(
        search_text=search_text,
        vector_queries=vector_queries,
        filter=odata_filter,
        select=["description", "category", "amount"],
        top=K,
    )
    return [f"{r['description']} ({r['category']}, {r['amount']})" for r in results]


for query in ["caffeine", "Lidl"]:
    print(f"\n=== {query!r}")
    for mode in ("keyword", "vector", "hybrid"):
        print(f"-- {mode}")
        for line in run(query, mode) or ["(no results)"]:
            print("   ", line)

print("\n=== 'food' with filter category eq 'Food' and amount gt 30 (hybrid)")
for line in run("food", "hybrid", "category eq 'Food' and amount gt 30") or ["(no results)"]:
    print("   ", line)
