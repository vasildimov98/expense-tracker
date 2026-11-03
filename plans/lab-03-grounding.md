# Lab 3: Grounding with Azure AI Search (vector + hybrid)

Builds on Labs 1-2 (see `plans/lab-spec.md`). Theory: Section 2 (retrieval, indexing, vector search) and P4 m8 (Azure AI Search).

## 1. Spec

**Goal.** Let the advisor answer questions about *the user's own spending* instead of general knowledge. Index expenses in Azure AI Search with embeddings, retrieve the relevant ones for a question, and have the model answer only from what was retrieved (grounding), citing the records.

**Requirements**
1. An Azure AI Search service and an index holding expenses with a text field, filterable fields and a vector field.
2. An embedding model deployment in the Foundry resource.
3. A build script that embeds expenses and uploads them. Re-running must not create duplicates.
4. A query script that retrieves (hybrid: keyword + vector, with an optional filter) and answers grounded on the results through the Lab 2 router.
5. Keyless access to Search (RBAC, no admin key in code). `app/` core stays Azure-free.

**Constraints.** `rg-expense-ai`, swedencentral, cheapest tier that works, no secrets in git.

### Decision table

| # | Decision | Why | Rejected alternative | Change when |
|---|---|---|---|---|
| D22 | Azure AI Search **Free** tier | $0, supports vector search, enough for a few hundred small docs (limits: 50 MB, 3 indexes, one free service per subscription) | Basic (~$70+/month, billed hourly while it exists): paying for replicas and capacity we don't need | More data or need for replicas/SLA, or Free isn't offered in the region |
| D23 | Embedding model `text-embedding-3-small` (1536 dims) | Cheapest current embedding model; quality is plenty for short expense text; fewer dimensions = smaller index | `text-embedding-3-large` (3072 dims): about 6x the price, bigger index, no gain on short text | Retrieval quality measured as poor on real data |
| D24 | One expense = one document, no chunking | Each record is a short sentence; chunking exists for long documents (statements, PDFs) so a chunk fits the model's context and stays on one topic | Chunking now: adds complexity for no benefit | Lab on receipts/statements (long text) |
| D25 | Embed a natural-language sentence per expense (`"Food: Starbucks latte, 4.5 on 2026-10-19"`), keep structured fields separate | The vector captures meaning; amounts/categories stay exact and filterable. Embeddings are bad at exact numbers | Embedding the raw JSON: noisy | Evaluation shows another text template retrieves better |
| D26 | **Hybrid** search (keyword + vector) plus `$filter` | Keywords catch exact terms ("Lidl"), vectors catch meaning ("coffee" finds "latte"); filters give exact constraints; results are merged with Reciprocal Rank Fusion | Vector-only (misses exact terms), keyword-only (misses synonyms) | Lab measures show one mode is enough |
| D27 | HNSW index, cosine similarity | Standard approximate nearest-neighbour algorithm, fast at scale; cosine suits text embeddings | Exhaustive KNN: exact but slower at scale | Tiny index where exact search is fine |
| D28 | Search access via RBAC roles, not admin keys | Same reasoning as D8: no secret, per identity, auditable. Three roles: *Search Service Contributor* (create index), *Search Index Data Contributor* (upload docs), *Search Index Data Reader* (query only: least privilege for the app) | Admin key in `.env`: full control, shared, never expires | Never for production |
| D29 | Deterministic document ids (`id` = hash of the expense) and `upload` as merge-or-upload | Re-running the build updates instead of duplicating (idempotent) | Auto ids: re-run doubles the index | Real ids exist in the store |
| D30 | Answer via `ask("advise", ...)` with a "answer only from the context, say so if missing" instruction | Reuses the router (D18); the instruction is what makes it *grounded*; citing ids lets the user verify | Letting the model answer freely: hallucinated numbers | Lab 7-8 (evaluators for groundedness) |

## 2. Prerequisites and cost

- Labs 1-2 working, venv active, `az login` active.
- `pip install azure-search-documents` (then `pip freeze` if the project pins requirements).
- **Quota check first (Lab 2 lesson).** Quota is per model and deployment type, and this subscription has tight limits:
  `az cognitiveservices usage list -l swedencentral -o json` and look for names containing `text-embedding-3-small`. Use a deployment type whose `limit` is above 0.
- **What bills:** embeddings are fractions of a cent for ~20 expenses; Free-tier Search is $0. **If you ever choose Basic or higher it bills per hour from creation until deletion**, even idle.
- **Cleanup:** `az search service delete -n <search-name> -g rg-expense-ai`, or delete the whole group at the end. Free services also stop being free if you create a second one: you get one per subscription.

## 3. Tasks

### Task 1: Create the search service

**Objective.** A Search service with RBAC enabled.

```bash
az search service create \
  --name <globally-unique-search-name> \
  --resource-group rg-expense-ai \
  --location swedencentral \
  --sku free \
  --auth-options aadOrApiKey \
  --aad-auth-failure-mode http401WithBearerChallenge
```

- The name becomes part of the endpoint `https://<name>.search.windows.net`, so it must be globally unique, lowercase, 2-60 chars.
- `aadOrApiKey` accepts both Entra tokens and keys, so nothing breaks while you learn; the code only uses tokens (D28).
- If the CLI refuses these flags on the Free tier, create it in the portal (Create a resource -> Azure AI Search -> Free) and then enable **Keys -> Both** (or Role-based access control) on the service's Keys blade. If Free is unavailable in swedencentral the error will say so: the portal shows which regions offer it.

**Roles for your user** (control-plane Owner/Contributor does not grant data access, same as Lab 1):

```bash
SEARCH_ID=$(az search service show -n <search-name> -g rg-expense-ai --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
for role in "Search Service Contributor" "Search Index Data Contributor" "Search Index Data Reader"; do
  az role assignment create --assignee "$ME" --role "$role" --scope "$SEARCH_ID"
done
```

Role assignments take a minute or two to propagate; a `403` right after is normal.

**Verify (UI).** Azure portal -> the search service -> Overview shows status Running and the URL. Indexes is empty for now.

### Task 2: Deploy the embedding model

```bash
az cognitiveservices account deployment create \
  --name expense-advisor-resource \
  --resource-group rg-expense-ai \
  --deployment-name text-embedding-3-small \
  --model-name text-embedding-3-small \
  --model-version 1 \
  --model-format OpenAI \
  --sku-name <Standard or GlobalStandard, whichever has quota> \
  --sku-capacity 10
```

If the version is rejected, `az cognitiveservices account list-models -n expense-advisor-resource -g rg-expense-ai -o table` shows valid versions.

Append to `.env` and `.env.example` (ending newline first):

```
AZURE_SEARCH_ENDPOINT=https://<search-name>.search.windows.net
AZURE_SEARCH_INDEX=expenses
FOUNDRY_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

### Task 3: A shared Search module and seed data

**Why.** Same rule as D11: one module knows how to authenticate to Search, and `app/ai/__init__.py` stays empty.

Create `app/ai/search_client.py`:

```python
"""Single place that knows how to talk to Azure AI Search."""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

load_dotenv()

ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
INDEX_NAME = os.environ["AZURE_SEARCH_INDEX"]
EMBEDDING_DEPLOYMENT = os.environ["FOUNDRY_EMBEDDING_DEPLOYMENT"]


def get_index_client() -> SearchIndexClient:
    # Manages indexes (create/delete): needs Search Service Contributor.
    return SearchIndexClient(ENDPOINT, DefaultAzureCredential())


def get_search_client() -> SearchClient:
    # Reads/writes documents inside one index.
    return SearchClient(ENDPOINT, INDEX_NAME, DefaultAzureCredential())
```

Seed data: the real `expenses.json` has only 2 rows, too few to see retrieval work. Create `app/ai/labs/lab03_seed_expenses.json` with ~20 rows in the same shape (`category`, `amount`, `description`, `date`). Vary the wording on purpose, for example:

```json
[
  {"category": "Food", "amount": 4.5, "description": "Starbucks latte", "date": "2026-10-02"},
  {"category": "Food", "amount": 62.3, "description": "Lidl weekly groceries", "date": "2026-10-04"},
  {"category": "Food", "amount": 38.0, "description": "Pizza dinner with friends", "date": "2026-10-09"},
  {"category": "Transport", "amount": 18.5, "description": "Uber ride to airport", "date": "2026-10-11"},
  {"category": "Transport", "amount": 45.0, "description": "Monthly metro pass", "date": "2026-10-01"},
  {"category": "Entertainment", "amount": 12.99, "description": "Netflix subscription", "date": "2026-10-05"},
  {"category": "Entertainment", "amount": 24.0, "description": "Cinema tickets", "date": "2026-10-17"},
  {"category": "Utilities", "amount": 71.2, "description": "Electricity bill October", "date": "2026-10-20"},
  {"category": "Utilities", "amount": 29.9, "description": "Internet and phone plan", "date": "2026-10-21"},
  {"category": "Other", "amount": 35.0, "description": "Gift for a colleague", "date": "2026-10-23"}
]
```

Extend it to about 20 (add a few more coffee/restaurant/ride-hailing items with *different words* than the ones above: "espresso", "cappuccino", "taxi", "bus ticket", "streaming service"). Different vocabulary is what makes the vector-vs-keyword experiment in Task 6 meaningful.

### Task 4: Build the index and load it

**Objective.** Create the index (schema) and upload embedded documents.

**Why this design.** The schema is the contract: `category` and `amount` are *filterable* (exact constraints), `description` is *searchable* (keyword), `content_vector` is the vector field with 1536 dimensions (must equal the embedding model's output size, otherwise uploads fail). The HNSW profile ties the vector field to the algorithm (D27).

Create `app/ai/labs/lab03_build_index.py`:

```python
import hashlib
import json
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

expenses = json.loads(
    (Path(__file__).parent / "lab03_seed_expenses.json").read_text()
)


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
print(f"Uploaded {sum(r.succeeded for r in result)}/{len(docs)} documents")
```

Run from the project root: `python -m app.ai.labs.lab03_build_index`.

**Expected output.** `Uploaded 20/20 documents` (your count). Run it twice: the count in the portal must not change (idempotent, D29).

**Common errors**
- `403 Forbidden`: roles not propagated yet, or a role is missing (index creation needs *Service Contributor*, upload needs *Data Contributor*).
- `The vector field 'content_vector' ... dimensions`: embedding size and `DIMENSIONS` disagree.
- `DeploymentNotFound`: `FOUNDRY_EMBEDDING_DEPLOYMENT` must be the deployment **name** (Labs 1-2 miss, third time).
- Empty `404` on `/embeddings` even though the deployment exists: the **project-scoped** endpoint (`.../api/projects/<project>/openai/v1/`, used by `get_openai_client()`) does not serve embeddings. Use the resource-level `.../openai/v1/` endpoint, which `get_embeddings_client()` builds from the same project endpoint with a keyless token provider (Lab 3 lesson).
- Connection/DNS error on the endpoint: typo in `AZURE_SEARCH_ENDPOINT`, or the service is still provisioning.

**Verify (UI).** Portal -> search service -> Indexes -> `expenses`: document count matches. Open **Search explorer**, run an empty search, and open one document: you should see the 1536-number `content_vector`.

### Task 5: Retrieve and answer (grounding)

**Objective.** Question in, answer out, based only on retrieved records.

**Why.** Retrieval turns the question into a vector (same embedding model as the index, always: vectors from different models are not comparable), asks Search for the nearest documents plus keyword matches, and the prompt forces the model to use only those. Without the "only from context" rule the model would fill gaps with plausible inventions.

Create `app/ai/labs/lab03_query.py`:

```python
import sys

from azure.search.documents.models import VectorizedQuery

from app.ai.foundry_client import get_embeddings_client
from app.ai.model_router import ask
from app.ai.search_client import EMBEDDING_DEPLOYMENT, get_search_client


def retrieve(question: str, k: int = 5, odata_filter: str | None = None) -> list[dict]:
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
```

Run: `python -m app.ai.labs.lab03_query "How much did I spend on coffee?"`

**Expected output.** An answer that names the coffee-like expenses with their ids and sums them, or says it is unsure. Check the sum yourself against the seed file: a grounded answer is *verifiable*, which is the point.

Also try a question the data cannot answer ("What did I spend in Japan?") and confirm it says it does not have that information.

**Common errors**
- Answer ignores your data: check `context` is actually filled (print it).
- A wrong total: the model did the arithmetic on only the top-k records. Retrieval returns the *most relevant* k, not all matching rows. Totals over many rows are a database job (aggregate in code or with Search facets), not an LLM job. This limitation is itself an exam-relevant point.

### Task 6: Compare retrieval modes (the experiment)

**Objective.** See why hybrid exists, with your own data.

Run `python -m app.ai.labs.lab03_compare_modes` (a scratch script) to call Search three ways for the query `"caffeine"`, a word that appears in none of your descriptions:

1. keyword only: `search_text="caffeine"`, no `vector_queries`
2. vector only: `search_text=None`, with the `VectorizedQuery`
3. hybrid: both

Then query `"Lidl"` the same three ways. Write down what each returns.

**Expected.** `"caffeine"`: keyword returns nothing (no literal match), vector and hybrid find the coffee drinks. `"Lidl"`: every mode ranks it first on a 21-document index (we measured it); vector-only is expected to drift only on a large index. Note that vector and hybrid always return k results, even irrelevant ones, while keyword returns only literal matches. That table is D26 in your own words.

Finally, try a filter: `odata_filter="category eq 'Food' and amount gt 30"`.

## 4. Verification (UI)

Portal -> search service -> Indexes -> `expenses` -> Search explorer. Run `caffeine` as JSON with a vector query is awkward by hand, so use the explorer for what it is good at: confirm document count, inspect a document, run a keyword query with `$filter=category eq 'Food'` and `$count=true`. Check **Monitoring** on the service for your query count.

## 5. Self-check (exam style)

1. You embed documents with `text-embedding-3-small`. A teammate embeds *queries* with `text-embedding-3-large`. What happens?
   A. Better accuracy  B. Retrieval silently degrades or fails: the vectors are not comparable and dimensions differ  C. Search converts them automatically  D. Nothing, vectors are universal
2. Which retrieval mode finds "latte" when the user asks about "coffee", AND still ranks an exact "Lidl" match first?
   A. Keyword  B. Vector  C. Hybrid  D. Facet
3. The app only needs to *query* the index. Which role follows least privilege?
   A. Owner  B. Search Service Contributor  C. Search Index Data Contributor  D. Search Index Data Reader
4. Why does the build script use deterministic ids and `merge_or_upload_documents`?
5. A grounded answer gives a wrong monthly total even though all the records are in the index. What is the likely cause, and what is the right fix?
6. In `embeddings.create(model=...)` what must the value be?

Send your answers and I will mark them.

## 6. Decision recap

Free tier Search (D22), cheap embedding model (D23), one document per expense (D24), natural-language embedding text plus separate exact fields (D25), hybrid with filters (D26), HNSW cosine (D27), RBAC least privilege (D28), idempotent loads (D29), and a grounding instruction with citations (D30). Retrieval returns the top-k, so aggregation belongs in code.

## 7. After the lab

Send me: the build output, three or four query outputs, your Task 6 observations and the self-check answers. I will log D22-D30 and the lessons in `plans/lab-spec.md`.
