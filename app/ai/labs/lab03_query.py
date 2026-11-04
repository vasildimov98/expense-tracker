import sys

from azure.search.documents.models import VectorizedQuery

from app.ai.model_router import ask
from app.ai.retrieval import retrieve



def answer(question: str, odata_filter: str | None = None) -> str:
    docs = retrieve(question, k=5, odata_filter=odata_filter)
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