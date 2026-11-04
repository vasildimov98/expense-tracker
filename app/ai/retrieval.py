"""Hybrid retrieval over the expenses index (keyword + vector + filter)."""
from azure.search.documents.models import VectorizedQuery

from app.ai.foundry_client import get_embeddings_client
from app.ai.search_client import EMBEDDING_DEPLOYMENT, get_search_client


def retrieve(question: str, k: int = 5, odata_filter: str | None = None) -> list[dict]:
    embedding = get_embeddings_client().embeddings.create(
        model=EMBEDDING_DEPLOYMENT, input=question
    ).data[0].embedding
    results = get_search_client().search(
        search_text=question,
        vector_queries=[VectorizedQuery(
            vector=embedding, k_nearest_neighbors=k, fields="content_vector")],
        filter=odata_filter,
        select=["id", "description", "category", "amount", "date"],
        top=k,
    )
    return [dict(r) for r in results]