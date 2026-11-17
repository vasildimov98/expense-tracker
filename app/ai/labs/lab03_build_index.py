import hashlib
import json
import os
from pathlib import Path

from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SearchableField,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

from app.ai.foundry_client import get_embeddings_client
from app.ai.search_client import (
    EMBEDDING_DEPLOYMENT, INDEX_NAME, get_index_client, get_search_client,
)

DIMENSIONS = 1536  # text-embedding-3-small output size

index = SearchIndex(
    name=INDEX_NAME,
    fields=[
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(name="description", type=SearchFieldDataType.String),
        SimpleField(name="category", type=SearchFieldDataType.String,
                    filterable=True, facetable=True),
        SimpleField(name="amount", type=SearchFieldDataType.Double,
                    filterable=True, sortable=True),
        SimpleField(name="date", type=SearchFieldDataType.String, sortable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=DIMENSIONS,
            vector_search_profile_name="hnsw-profile",
        ),
    ],
    vector_search=VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw")],
        profiles=[VectorSearchProfile(name="hnsw-profile",
                                      algorithm_configuration_name="hnsw")],
    ),
)
get_index_client().create_or_update_index(index)  # safe to re-run

# Lab 7: SEED_PATH lets the same script build the poisoned test index (with AZURE_SEARCH_INDEX set too).
SEED_PATH = os.environ.get("SEED_PATH", str(Path(__file__).parent / "lab03_seed_expenses.json"))
expenses = json.loads(Path(SEED_PATH).read_text())


def to_text(e: dict) -> str:
    # D25: natural-language sentence for the embedding, structured fields stay separate.
    return f"{e['category']}: {e['description']}, {e['amount']} on {e['date']}"


def to_id(e: dict) -> str:
    # D29: deterministic id, so re-running updates instead of duplicating.
    return hashlib.sha1(to_text(e).encode()).hexdigest()


# One embeddings call for the whole batch: fewer round trips, same cost.
response = get_embeddings_client().embeddings.create(
    model=EMBEDDING_DEPLOYMENT,          # the deployment NAME, again
    input=[to_text(e) for e in expenses],
)

docs = [
    {
        "id": to_id(e),
        "description": e["description"],
        "category": e["category"],
        "amount": float(e["amount"]),
        "date": e["date"],
        "content_vector": item.embedding,
    }
    for e, item in zip(expenses, response.data)
]

result = get_search_client().merge_or_upload_documents(docs)
print(f"Index {INDEX_NAME}: uploaded {sum(r.succeeded for r in result)}/{len(docs)} documents")