import sys

from azure.search.documents.models import VectorizedQuery

from app.ai.foundry_client import get_embeddings_client
from app.ai.model_router import ask
from app.ai.search_client import EMBEDDING_DEPLOYMENT, get_search_client


def retrieve(question: str, k: int = 10, odata_filter: str | None = None) -> list[dict]:
    embedding = get_embeddings_client().embeddings.create(
        model=EMBEDDING_DEPLOYMENT, input=question
    ).data[0].embedding
    results = get_search_client().search(
        search_text=question,                                # keyword half
        vector_queries=[VectorizedQuery(                     # vector half
            vector=embedding, k_nearest_neighbors=k, fields="content_vector")],
        filter=odata_filter,                                 # exact constraints
        select=["id", "description", "category", "amount", "date"],
        top=k,
    )
    return [dict(r) for r in results]


def answer(question: str, odata_filter: str | None = None) -> str:
    docs = retrieve(question, odata_filter=odata_filter)
    context = "\n".join(
        f"[{d['id'][:6]}] {d['date']} {d['category']}: {d['description']} ({d['amount']})"
        for d in docs
    )
    instructions = (
        "You are a concise financial advisor. Answer ONLY from the expense "
        "records below. If they do not contain the answer, say you do not "
        "have that information. Cite the record ids in square brackets.\n\n"
        f"Records:\n{context}"
    )
    return ask("advise", instructions, question, max_output_tokens=300)


if __name__ == "__main__":
    question = " ".join(sys.argv[1:]) or "How much did I spend on coffee?"
    print(answer(question))