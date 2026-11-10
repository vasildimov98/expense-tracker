# Lab 6: Operate it (quotas, cost, monitoring, identity, networking)

Builds on Labs 1-5 (see `plans/lab-spec.md`). Theory: Section 3, "Manage, Monitor, and Secure" (quotas and 429s, cost, model monitoring, ingestion and index health, keyless access, private networking, the Halcyon launch-day incident).

Exam objectives covered:
- Manage quotas, scaling, rate limits and cost footprints for model and agent workloads
- Monitor model performance, drift, safety events and grounding quality
- Monitor data ingestion quality, search index health and relevance
- Configure security: managed identity, private networking, keyless credentials, role policies

## 1. Spec

**Goal.** The Expense Advisor survives its own "launch day": a burst of traffic produces `429`s that the app absorbs instead of showing errors, every call leaves a cost and latency record, the search index is checked against its source of truth, access is least-privilege and keyless, and the AI account can be closed to the public internet.

**Requirements**
1. Calls to Foundry retry on `429` with backoff, respect `Retry-After`, and fail over to a second deployment when the first stays throttled. All of it is unit-tested **without Azure** (principle 5).
2. Every model call logs: task, deployment, input/output tokens, latency, estimated cost. A daily token cap stops a runaway loop before the bill does (D14: no Cost Management on this subscription).
3. Traces and metrics reach Azure Monitor (Application Insights + Log Analytics), and you can answer three questions in KQL: how many 429s, how many tokens per deployment, what is p95 latency.
4. A health check compares the search index with the source data (document count) and runs a small set of known queries to detect relevance regressions.
5. Identity audit: every role assignment has a reason, no API keys work, and a user-assigned managed identity exists with only the roles the running app needs.
6. A test environment has a private endpoint and public access disabled; you observe your own laptop being refused, then undo it.

**Constraints.** I only write code and commands, **you run them** (see memory: no Azure calls from my side). Tasks 1-5 use the existing `rg-expense-ai`. Task 6 uses a **separate, throwaway** resource group so a networking mistake cannot lock you out of the working environment.

### Decision table

| # | Decision | Why | Rejected alternative | Change when |
|---|---|---|---|---|
| D57 | Retry `429` with **exponential backoff + jitter**, honor `Retry-After` when the service sends it | A 429 is a "slow down" signal, not a failure. Immediate retries from many clients arrive together and throttle again (retry storm); jitter spreads them. The server's `Retry-After` is better information than our guess | No retry (user sees errors); fixed sleep (synchronized retries) | Never; but cap total attempts and total wait so a user never waits minutes |
| D58 | **Fail over** to a second deployment after retries are exhausted (gpt-4o Standard -> same-family fallback) | Quota is per deployment (D20), so a second deployment is a second pool of capacity. Cheaper than raising capacity permanently for a rare burst | Raising capacity (D6 says capacity is also a cost brake); a gateway (API Management) is the production answer, overkill here | Sustained traffic: provisioned throughput or a gateway with load balancing |
| D59 | Keep **capacity low (10)** and absorb bursts in code | Capacity is a spend-speed brake (D6). Backoff handles short bursts; a permanent raise hides bugs (loops) | Raising TPM "to be safe" | Measured p95 load shows throttling is the normal state, not the exception |
| D60 | **Token and cost accounting in our own code** (usage from every response) | The portal shows totals per deployment, not per task or feature, and this subscription has no budget alerts (D14). Per-task numbers drive routing decisions (D18) | Reading only the Monitor tab | Cost Management becomes available: add budgets and alerts on top, keep the per-task log |
| D61 | A **daily token cap** enforced before the call | Cost control that works without the platform. Failing closed is the point: an agent loop is the classic runaway | Trusting `max_output_tokens` alone (bounds one call, not the count of calls) | Never |
| D62 | **OpenTelemetry to Application Insights** (workspace-based) | Vendor-neutral instrumentation; Foundry's Tracing tab reads the same data; Log Analytics gives KQL and retention control | Print statements; a third-party APM | The company standard is another backend (OpenTelemetry still applies) |
| D63 | **Do not record prompt/response content** in traces by default | Expense data is personal data. Metadata (tokens, latency, ids) answers operational questions; content capture is opt-in per debugging session | Always on "for debugging" | A privacy review approves content capture with retention and access limits |
| D64 | **Index health = count parity + a golden query set** | Count parity detects failed ingestion (documents dropped silently); golden queries detect relevance regressions after a re-index or model change. The Lab 3 `Japan` case showed a vector query always returns k results, so "returned something" is not a health signal | Only checking that the service is up | Index grows large: sample parity, add an indexer-status check when an indexer is used |
| D65 | **User-assigned managed identity** with only runtime roles: Foundry User on the project scope, Search Index Data Reader on the service | A user-assigned identity survives the app being rebuilt and can be granted roles before the app exists. System-assigned dies with the resource. Least privilege (Lab 3 lesson: query-only needs Reader) | Using your personal identity in production; Contributor "to make it work" | Many identical workloads share one identity badly: split per workload for a smaller blast radius |
| D66 | Roles at the **narrowest scope** (project/service, not subscription) | A leaked token can only do what the role allows where it applies | Subscription-wide roles | Never |
| D67 | **Private endpoint + public access disabled** tested in a throwaway group | The only way to prove "closed to the internet" is to be refused from outside. A throwaway keeps the main environment reachable | Doing it on `rg-expense-ai` | Production: put it in the template (Lab 5 pattern) with private DNS and a jump host or VPN for people |

## 2. Prerequisites and cost

- Labs 1-5 done, `az login` active, venv active, `rg-expense-ai` exists with the gpt-4.1-mini, gpt-4o and embedding deployments and the Search service.
- **Cost, honestly:**
  - Task 1 burst test: a few hundred small requests on gpt-4.1-mini = **cents**. Use the `max_output_tokens=20` shown.
  - Application Insights / Log Analytics: first 5 GB per month ingestion is free; this lab sends kilobytes.
  - UAMI and role assignments: free.
  - Task 6 private endpoint: about **$0.01 per hour** plus a private DNS zone (cents) and a VNet (free). Delete the same day. Forgotten, it costs about $7-8 per month.
- **Cleanup (end of lab):** Section 7.
- **Not verified by me:** property names and API versions in Bicep, KQL table/column names, and the exact telemetry package names. Treat errors as part of the lab and paste them to me.

## 3. Tasks

### Task 1: Survive a 429 (D57-D59)

**Objective.** Make a burst of requests succeed through retries and failover, and prove the logic with tests.

**Why.** The Halcyon case study is exactly this: launch-day traffic exceeds the TPM cap. The exam asks what to do first (retry with backoff), what to do when it persists (more capacity, another deployment, a gateway), and which numbers prove it (429 rate, remaining-tokens header).

**Step 1.1: reproduce the problem first (so you see what you are fixing).**
Create `app/ai/labs/lab06_burst.py`:

```python
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
```

Run: `python -m app.ai.labs.lab06_burst`

Expected: a mix of `ok` and `429 (retry-after=...)`. If you get zero 429s, raise `range(120)` to 400 or lower the deployment capacity temporarily (portal: Deployments -> edit -> capacity 1); note which you did.

**Step 1.2: the resilient wrapper.** Create `app/ai/resilience.py`:

```python
"""Retry with backoff on 429, then fail over to a fallback deployment."""
import random
import time
from typing import Callable, TypeVar

import openai

T = TypeVar("T")

MAX_ATTEMPTS = 4          # per deployment
BASE_DELAY = 1.0          # seconds
MAX_DELAY = 20.0
TOTAL_BUDGET = 45.0       # a user never waits longer than this


def _delay(attempt: int, retry_after: float | None) -> float:
    if retry_after is not None:               # the server knows best
        return min(retry_after, MAX_DELAY)
    backoff = min(MAX_DELAY, BASE_DELAY * 2 ** attempt)
    return random.uniform(0, backoff)          # full jitter


def _retry_after(error: openai.RateLimitError) -> float | None:
    value = error.response.headers.get("retry-after")
    try:
        return float(value) if value is not None else None
    except ValueError:
        return None


def call_with_retry(
    fn: Callable[[str], T],
    deployments: list[str],
    sleep: Callable[[float], None] = time.sleep,
    now: Callable[[], float] = time.monotonic,
) -> T:
    """fn(deployment_name) is tried on each deployment in order."""
    started = now()
    last_error: Exception | None = None
    for deployment in deployments:
        for attempt in range(MAX_ATTEMPTS):
            try:
                return fn(deployment)
            except openai.RateLimitError as error:
                last_error = error
                wait = _delay(attempt, _retry_after(error))
                if now() - started + wait > TOTAL_BUDGET:
                    break                      # give up on this deployment
                sleep(wait)
    raise last_error or RuntimeError("no deployments configured")
```

Why the injected `sleep` and `now`: tests run instantly and deterministically.

**Step 1.3: tests** in `tests/test_resilience.py`. Build a fake `RateLimitError` (needs an `httpx.Response`), then assert:
1. succeeds on the 3rd attempt on the primary (no failover used);
2. primary always 429 -> the fallback deployment is called and succeeds;
3. `Retry-After: 3` makes the wait exactly 3 (use a recording `sleep`);
4. all deployments fail -> raises the last `RateLimitError`;
5. a **non-429 error** (for example `openai.BadRequestError`) is **not** retried.

Mutation check (Lab 5 lesson): remove the `break`/budget check and confirm a test fails. If no test notices, your tests are too weak.

**Step 1.4: wire it in.** In `model_router.ask`, replace the direct call with `call_with_retry(lambda d: _client().responses.create(model=d, ...), [deployment_for(task), *fallbacks(task)])`. Add `FOUNDRY_FALLBACK_<TASK>` env vars (optional, empty means no failover) and document them in `.env.example`. Re-run the burst through `ask` and compare the counts with Step 1.1.

**Common errors.** `with_options(max_retries=0)` disables the SDK's built-in retries so you see raw 429s; in the real wrapper keep the SDK default at `0` too, otherwise two layers retry and multiply (4 x 2 attempts, unclear waits). Retrying on `APIConnectionError` and `5xx` is reasonable but is a separate decision, not part of this lab.

**Expected outcome.** Burst through the wrapper: all `ok`, with a longer total time. Tests green, no network.

### Task 2: Know what each call costs (D60-D61)

**Objective.** One log line per call with task, tokens, latency and cost, plus a daily cap.

**Why.** The portal cannot tell you "categorize costs $0.40 per 1000 items and advise costs $3". Your routing decision (D18) assumed this; now you measure it in production terms.

Create `app/ai/usage.py`:

```python
"""Per-call usage log and a daily token cap."""
import json
import logging
import threading
from datetime import date

log = logging.getLogger("expense_ai.usage")

# USD per 1M tokens (Azure Retail Prices API, D21). Re-check before relying on them.
PRICES = {
    "gpt-4.1-mini": (0.40, 1.60),
    "gpt-4o": (3.025, 12.10),
}
DAILY_TOKEN_CAP = 200_000

_lock = threading.Lock()
_state = {"day": date.today(), "tokens": 0}


class DailyCapExceeded(RuntimeError):
    pass


def check_cap() -> None:
    with _lock:
        if _state["day"] != date.today():
            _state.update(day=date.today(), tokens=0)
        if _state["tokens"] >= DAILY_TOKEN_CAP:
            raise DailyCapExceeded(f"{_state['tokens']} tokens used today")


def record(task: str, model: str, usage, latency_s: float) -> None:
    in_price, out_price = PRICES.get(model, (0.0, 0.0))
    cost = (usage.input_tokens * in_price + usage.output_tokens * out_price) / 1e6
    with _lock:
        _state["tokens"] += usage.input_tokens + usage.output_tokens
    log.info(json.dumps({
        "task": task, "model": model,
        "in": usage.input_tokens, "out": usage.output_tokens,
        "latency_s": round(latency_s, 3), "cost_usd": round(cost, 6),
    }))
```

Call `check_cap()` before and `record()` after every `responses.create` (in `model_router.ask` and the agent loop in `advisor_agent.chat`). Tests: cap raises when the counter is at the limit, cost math for a known usage (10 in / 5 out tokens on mini = exact value), the counter resets on a new day (monkeypatch `date`).

**Verification (UI).** Foundry portal -> Monitor: compare total tokens for the deployment with the sum of your log lines for the same hour. They should be close; a gap means a call path that bypasses `record`.

**Common errors.** The model name returned in `response.model` is the model, not the deployment; key your prices by what you actually have. Logging full prompts here would break D63 - log numbers only.

### Task 3: Telemetry in Azure Monitor (D62-D63)

**Objective.** Traces and your usage log arrive in Application Insights; answer three questions in KQL.

**Steps.**
1. Portal: Foundry project -> Tracing (or Monitoring) -> connect/create **Application Insights** (workspace-based). If you prefer the CLI: `az monitor log-analytics workspace create` then `az monitor app-insights component create --workspace <id> ...`.
2. Install and wire (verified 2026-11-10: `azure-monitor-opentelemetry==1.8.12`; the Foundry SDK already ships `AIProjectInstrumentor`, so no separate OpenAI instrumentation package is needed). Read the connection string from the project instead of copying it by hand (it is a secret-adjacent value). The working code is `app/ai/telemetry.py`; the snippet below is the idea:
   ```python
   # app/ai/telemetry.py
   from azure.monitor.opentelemetry import configure_azure_monitor
   from app.ai.foundry_client import get_project_client

   def setup() -> None:
       conn = get_project_client().telemetry.get_application_insights_connection_string()
       configure_azure_monitor(connection_string=conn)
   ```
   Keep message-content capture **off** (D63); the environment variable that controls it is documented with the instrumentation package you install. Call `setup()` from your entry points, never at import time (tests must stay offline).
3. Run the chat script and the burst again, wait 2-5 minutes.
4. Application Insights -> Logs. Starting points (table and column names differ by version; open the table list on the left and adjust):
   ```kusto
   // 1) throttling: requests by result code
   AppRequests
   | where TimeGenerated > ago(1h)
   | summarize count() by ResultCode

   // 2) tokens per deployment from your own log lines
   AppTraces
   | where Message startswith "{"
   | extend j = parse_json(Message)
   | summarize tokens = sum(toint(j["in"]) + toint(j["out"])), cost = sum(todouble(j.cost_usd)) by model = tostring(j.model)

   // 3) p95 latency per task
   AppTraces
   | where Message startswith "{"
   | extend j = parse_json(Message)
   | summarize p95 = percentile(todouble(j.latency_s), 95) by tostring(j.task)
   ```
   Column and table names may differ in your workspace; adjust from the schema list if a query fails.
5. Portal alert (UI): Azure Monitor -> Alerts -> new rule on the account metric "Azure OpenAI Requests" filtered by status `429`, threshold you choose, action group = your email. **Why:** a dashboard nobody watches is not monitoring.

**Drift and safety signals (theory made concrete).** Add one dimension to your usage log now: `finish_reason`/`status` of every response (`completed`, `incomplete`, `content_filter`). A rising share of `incomplete` means `max_output_tokens` is too low; a rising `content_filter` share is a safety event (Lab 7 reads this).

**Expected outcome.** The three queries return rows; you can state the 429 rate during your burst.

### Task 4: Index health and relevance (D64)

**Objective.** A script that returns PASS/FAIL for the Search index.

**Why.** Silent ingestion failures and relevance regressions look like "the model got dumber". Check the data layer first.

Create `app/ai/labs/lab06_index_health.py`:

```python
"""Index health: count parity + golden queries (hit@k)."""
import json
import os
import sys

from azure.search.documents.indexes import SearchIndexClient
from azure.identity import DefaultAzureCredential

from app.ai.retrieval import retrieve

GOLDEN = [   # (query, id that MUST appear in the top k)  - fill from lab03_seed_expenses.json
    ("coffee", "<id of a coffee expense>"),
    ("supermarket groceries", "<id of a Lidl expense>"),
    ("monthly streaming subscription", "<id of Netflix>"),
]
K = 5


def main() -> int:
    source = json.load(open(os.environ["EXPENSES_PATH"]))
    index_client = SearchIndexClient(os.environ["AZURE_SEARCH_ENDPOINT"], DefaultAzureCredential())
    stats = index_client.get_index_statistics(os.environ["AZURE_SEARCH_INDEX"])
    ok = True

    print(f"source={len(source)} index={stats['document_count']} storage={stats['storage_size']}B")
    if stats["document_count"] != len(source):
        print("FAIL: count mismatch (dropped or duplicated documents)")
        ok = False

    hits = 0
    for query, expected_id in GOLDEN:
        ids = [d["id"] for d in retrieve(query, k=K)]
        found = expected_id in ids
        hits += found
        print(("PASS" if found else "FAIL"), query, "->", ids)
    print(f"hit@{K}: {hits}/{len(GOLDEN)}")
    return 0 if ok and hits == len(GOLDEN) else 1


sys.exit(main())
```

Fill the ids from the seed file (open `app/ai/labs/lab03_seed_expenses.json`). Check `retrieve` returns dicts with `id` (print one result first); adapt if the key differs.

**Break it on purpose.** (a) Delete one document in the portal's Search explorer, or change the seed path, and confirm the count check fails. (b) Re-run `lab03_build_index.py` and confirm it is back to PASS (D29 idempotency). Write down what each failure would mean in production (ingestion dropped rows vs source changed vs duplicates).

**UI check.** Search service -> Monitoring: queries per second, latency, throttled queries; Indexes: document count and storage against the Free tier cap (50 MB / 3 indexes, D22).

### Task 5: Identity audit and managed identity (D65-D66, D45)

**Objective.** Prove keyless, list who can do what, create the identity the running app should use.

**Step 5.1: prove keys are dead (account created by Bicep has `disableLocalAuth: true`; the hand-made `rg-expense-ai` may not).**
```bash
az cognitiveservices account show -g rg-expense-ai -n <resource> --query "properties.disableLocalAuth"
```
If `false` or `null`, decide: set it now (`az resource update ... --set properties.disableLocalAuth=true`) and re-run a script to confirm nothing used keys. Record the result. Search has a similar switch: `az search service update ... --disable-local-auth true` (flag name: check `--help`).

**Step 5.2: the role matrix.** Fill this table from `az role assignment list --all --assignee <you> -o table` and the portal's Access control (IAM) blade:

| Principal | Scope | Role | Why it needs it | Could it be narrower? |
|---|---|---|---|---|
| you (developer) | ... | ... | ... | ... |
| pipeline app (`gh-expense-advisor-test`) | rg-expense-ai-test (deleted) | Contributor | deploy | already narrow (D52) |
| **app runtime identity (new)** | project | Foundry User | call models, run agents | |
| **app runtime identity (new)** | search service | Search Index Data Reader | query only (Lab 3) | per-index scope is possible |

**Step 5.3: create the runtime identity and its roles.**
```bash
az identity create -g rg-expense-ai -n id-expense-advisor-app -l swedencentral
PRINCIPAL=$(az identity show -g rg-expense-ai -n id-expense-advisor-app --query principalId -o tsv)
az role assignment create --assignee-object-id $PRINCIPAL --assignee-principal-type ServicePrincipal \
  --role "Azure AI User" --scope <project resource id>
az role assignment create --assignee-object-id $PRINCIPAL --assignee-principal-type ServicePrincipal \
  --role "Search Index Data Reader" --scope <search service resource id>
```
(The role named "Foundry User" in the portal may still be accepted by name `Azure AI User` in the CLI; if the name is rejected, use the role ID from `az role definition list`.) Add the identity and its two role assignments to `scripts/azure/rebuild.sh` (principle 3 and the account-switch rule) - **roles stay human-run (D48)**.

**Step 5.4: negative test.** Portal -> Search service -> Access control (IAM) -> "Check access" on the new identity: it must show Reader but **not** Contributor. Then answer: if this identity's token leaked, what could the attacker do, and what could they not do? (You can read documents and call models in this project; you cannot change the index, delete deployments or read other resources.)

**Why you cannot test it end to end here.** Using the identity for real needs a host (App Service, Container Apps) - out of scope for cost. The exam only needs you to know the pattern: assign the identity to the host, `DefaultAzureCredential(managed_identity_client_id=...)` picks it up, no code change (D8).

### Task 6: Private networking in a throwaway (D67)

**Objective.** See "Public access disabled" refuse your laptop, and know what a private endpoint, private DNS zone and VNet each contribute.

**Why.** Exam scenarios ask: why does the app still resolve a public IP after you created the endpoint (missing private DNS zone link)? Why can your laptop no longer call the model (public access disabled, no route in)? Why do agents need more than a private endpoint (the agent runtime itself needs network injection into a delegated subnet)?

**Steps.**
1. New group `rg-expense-ai-net` and a small AI account **with no model deployments** (or reuse `infra/test.bicepparam` with the deployment array empty; this keeps Lab 5 working). No tokens are billed.
2. Write `infra/network-test.bicep` (new file; validate with `az bicep build` and `what-if`). It needs: a VNet with one subnet; a private endpoint targeting the account with group id `account`; private DNS zones `privatelink.cognitiveservices.azure.com`, `privatelink.openai.azure.com`, `privatelink.services.ai.azure.com`, each linked to the VNet; and a DNS zone group on the endpoint. Property names/API versions: look them up in the Bicep reference; this is the exercise.
3. Before turning public access off, run `nslookup <resource>.cognitiveservices.azure.com` from your laptop: public IP. That is correct, your laptop is outside the VNet.
4. Set `publicNetworkAccess: 'Disabled'` (template parameter, redeploy). Call the account from your laptop (any `az rest` GET against the data plane is enough): expect `403` with a message about public access. **Paste the exact message.**
5. Portal: account -> Networking shows "Disabled" with the private endpoint connection "Approved".

**Cleanup this task immediately:** `az group delete -n rg-expense-ai-net --yes`, then purge the soft-deleted account (Lab 5 lesson).

**Theory to write in your notes (3 lines, no steps).** Private endpoint = a private IP in your subnet for the service; private DNS zone = makes the service name resolve to that IP inside the VNet; agents on Foundry need the agent subnet delegated for network injection and are a bigger setup (no lab).

## 4. Verification checklist

- Burst test: raw run shows 429s; wrapper run all `ok`; `pytest -q` green.
- Usage log lines match the Monitor tab totals within a reasonable margin.
- KQL returns 429 count, tokens per model, p95 latency; one alert rule exists.
- Index health prints PASS; with a deleted document it FAILs on count.
- `disableLocalAuth` is true (or you recorded why not); role matrix filled; UAMI has exactly 2 assignments.
- Private endpoint test: you captured the 403 for public access; `rg-expense-ai-net` deleted and account purged.

## 5. Self-check (exam style)

1. A launch-day burst returns `429` for 8% of requests. Which action should come first? A. Raise `max_output_tokens` B. Retry with exponential backoff and jitter C. Switch the model to a larger one D. Disable the content filter
2. Why does adding jitter to the backoff matter?
3. Your quota for a model in a region is exhausted by one deployment. Name two ways to get more capacity or throughput without a code change to the app.
4. A cost alert is not available on your subscription. Name two controls that still bound cost, and what each one does NOT bound.
5. The app suddenly answers worse after nobody changed code. Which three data-layer checks do you run before blaming the model?
6. Why a user-assigned rather than system-assigned managed identity for the app? When would system-assigned be better?
7. After creating a private endpoint, the app still resolves the public IP of the account. What is missing?
8. You disabled public network access and your Foundry **agents** still fail while plain model calls from inside the VNet work. Why?

Send answers and I will mark them.

## 6. Decision recap

Treat `429` as a signal and absorb it (D57), buy more capacity in the cheapest way (D58-D59), measure per task what you spend (D60-D61), watch the system with vendor-neutral telemetry that does not leak personal data (D62-D63), check the data layer before the model (D64), give the app an identity that can do the minimum (D65-D66), and prove a closed network by being refused (D67).

## 7. Cleanup

```bash
az group delete -n rg-expense-ai-net --yes
az cognitiveservices account list-deleted -o table
az cognitiveservices account purge -n <name> -g rg-expense-ai-net -l swedencentral
# Optional: remove the Application Insights component and workspace if you do not need them for Labs 7-8 (they are reused there).
```
Keep `id-expense-advisor-app` (free) and the Application Insights component (Labs 7 and 8 reuse it).

## 8. After the lab

Send me: burst outputs (before/after), pytest results including your mutation check, a few usage log lines, KQL results, the index-health output (PASS and the deliberate FAIL), the filled role matrix, the 403 message from Task 6, and the self-check answers. I will log D57-D67 and the lessons in `plans/lab-spec.md`, update `scripts/azure/rebuild.sh`, and commit.
