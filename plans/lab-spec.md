# Expense Advisor: Lab Spec (living document)

One system built incrementally while studying for AI-103. Every lab adds a layer. Every decision below has a reason, so the whole picture stays visible.

## 1. System goal

**Expense Advisor**: an enterprise-style tracker that categorizes expenses, answers questions about spending (grounded on the user's own data), and acts as a financial advisor agent. The existing Python app (`app/`, `expenses.json`) is the domain core. Azure/Foundry code lives in `app/ai/`.

Design principles (apply to every lab):
1. **Keyless**: identity-based auth, no secrets in code or git.
2. **Cheapest thing that meets the requirement**: small models and pay-per-token first, upgrade only with a reason.
3. **Everything reproducible**: CLI/SDK for anything we'd want to repeat, UI for discovery, verification and monitoring.
4. **One resource group per lab environment**: cleanup is one command, blast radius is small.
5. **Core stays independent of Azure**: `app/` must run and test without Azure configured.

## 2. Architecture roadmap

| Layer | Component | Lab | Exam objective |
|---|---|---|---|
| Foundation | Foundry resource + project, model deployment, keyless auth | 1 (done) | Set up AI solutions in Foundry |
| Model strategy | SLM vs LLM routing, comparison, deployment types | 2 | Choose models and services |
| Grounding | Statements/receipts in Azure AI Search (vector index) | 3 | Retrieval, indexing, vector search |
| Agent | Advisor agent with memory, tools (existing app code), knowledge | 4 | Memory, tool, knowledge integration |
| Delivery | IaC, env config, CI/CD pipeline | 5 | Integrate with CI/CD |
| Ops (half 2) | Quotas, cost, monitoring, managed identity, private networking | 6 | Manage, monitor, secure |
| Safety (half 2) | Content filters, evaluators, tracing/audit, tool-access control | 7-8 | Responsible AI |

Labs 6-8 wait until the theory is covered (theory first).

## 3. Decision log

Format: **Decision / Why / Trade-off or alternative / When we'd change it.**

### Lab 1: Foundation

**D1. Foundry resource with a project (`expense-advisor-resource` / `expense-advisor`)**
- *Why:* the project is the unit that holds agents, files and connections for one app; the resource holds models and security. One resource can host many projects, so later labs add projects, not new resources.
- *Alternative:* the auto-created default project (`vasildimov91-2190`). Rejected because it lives in an auto-named resource group, which makes cleanup riskier.
- *Change when:* we need dev/test/prod separation, which means one project (or resource) per environment.

**D2. Dedicated resource group `rg-expense-ai`**
- *Why:* one-command cleanup, RBAC and budgets scoped to one place, nothing unrelated gets deleted.
- *Change when:* environments split (for example `rg-expense-ai-dev` / `-prod`).

**D3. Region `swedencentral`**
- *Why:* offers the model we need; keeping every resource in one region avoids cross-region latency and keeps quota in one place (quota is per region and subscription).
- *Trade-off:* not necessarily the nearest region; chosen for model availability.
- *Change when:* data residency, latency or quota requires another region.

**D4. Model `gpt-4.1-mini`**
- *Why:* categorizing an expense is a simple, high-volume task. A small, cheap, fast model is enough, and cost per request matters at volume.
- *Alternative:* a full-size LLM. Costs more per token and is slower for no quality gain on this task.
- *Change when:* Lab 2 compares it with a larger model for the advisory (reasoning-heavy) task.

**D5. Deployment type `GlobalStandard`**
- *Why:* pay per token, nothing billed while idle, and the highest default quota; right for development and variable load.
- *Trade-off:* requests may be processed in any region (data at rest stays in the resource's region), and latency is variable under load.
- *Alternatives:* `Standard` (regional processing), `DataZoneStandard` (EU/US boundary), `GlobalProvisionedManaged` (reserved throughput, hourly billing, predictable latency).
- *Change when:* steady, latency-critical production volume (provisioned), or data-residency rules (regional/data zone).

**D6. Capacity 10 (10K tokens per minute)**
- *Why:* a throttle on how fast spend can accumulate. A bug in a loop gets `429` errors instead of a big bill. It limits *speed* of spending, not total spend.
- *Change when:* real load is measured (Lab 6).

**D7. Pinned model version `2025-04-14`**
- *Why:* reproducible behavior; an unannounced model change could break categorization results.
- *Trade-off:* models retire on a schedule, so versions must be revisited.

**D8. Keyless auth: `DefaultAzureCredential` plus the Foundry User role (formerly Azure AI User)**
- *Why:* no secret exists to leak or rotate; access is per identity (least privilege, revocable, auditable); the same code works locally (`az login`) and in Azure (managed identity).
- *Key point:* Owner/Contributor are control-plane roles and do not grant calling the model (data plane), so the data-plane role is separate.
- *Alternative:* API key. Rejected: shared, long-lived, full access, no audit by identity.

**D9. Responses API (`client.responses.create`)**
- *Why:* it is the stateful, agent-ready API, so the same pattern carries into the agent labs. Chat Completions is stateless and would need rework.

**D10. `max_output_tokens` set on every call**
- *Why:* a hard cap on output size per request, so cost per call stays bounded.

**D11. One client module, `app/ai/foundry_client.py`**
- *Why:* a single place for auth and endpoint, so every later feature reuses it and a change (endpoint, credential, retries) happens once.
- *Rule:* `app/ai/__init__.py` stays empty. An import inside it would load the Azure client and demand environment variables for any `app.ai` import, which breaks tests and non-Azure runs.

**D12. Config in `.env`, `.env.example` committed**
- *Why:* secrets and environment-specific values stay out of git; the example file documents what is required. Env vars are the standard way to inject config in CI/CD and Azure hosting.

**D13. CLI for deployment, portal for creation and monitoring**
- *Why:* CLI commands are repeatable and scriptable (the base for Lab 5 CI/CD) and match the exam's developer focus; the UI is better for discovery and for visual verification.

**D14. Budget alerts unavailable on this subscription**
- *Fact:* Foundry showed "offer type isn't supported by Azure Cost Management".
- *Consequence:* the guardrails are D6 (TPM cap), D2 (one group to delete) and manual checks on the Monitor tab.
- *Change when:* moving to a subscription type that supports Cost Management.

### Lab 3: Grounding with Azure AI Search

**D22. Azure AI Search Free tier.** $0 while idle, supports vector search; limits 50 MB / 3 indexes, one free service per subscription. Kept after the lab because Lab 4 reuses the index (Free services may be removed after long inactivity; the build script recreates everything). *Alternative:* Basic (~$70+/month, hourly billing). *Change when:* more data, replicas or SLA are needed.

**D23. Embedding model `text-embedding-3-small` (1536 dims), GlobalStandard, capacity 10.** Cheapest current embedding model, enough for short text. Quota for it was 1000 units, no issue. *Alternative:* `-large` (3072 dims, ~6x price).

**D24. One expense = one document, no chunking.** Chunking is for long documents; revisit for statements and receipts.

**D25. Embed a natural-language sentence, keep structured fields separate.** Vectors capture meaning; amount and category stay exact and filterable.

**D26. Hybrid search plus `$filter`.** Observed on our 21 documents: for "caffeine" keyword returned nothing while vector and hybrid found the coffee rows; for "Lidl" every mode ranked it first (vector-only drifting is expected only at scale). A vector query always returns k results, even irrelevant ones (Cinema, Netflix for "caffeine"), so there is no built-in "no match": keyword gives an honest empty result, and the grounded prompt must say "I don't know".

**D27. HNSW, cosine.** Standard approximate nearest-neighbour setup.

**D28. Search access via RBAC, no admin keys.** Roles: Service Contributor (create index), Index Data Contributor (upload), Index Data Reader (query: what the app should hold). Setup `aadOrApiKey` was accepted on the Free tier.

**D29. Deterministic ids plus `merge_or_upload_documents`.** Re-running the build keeps 21 documents instead of duplicating.

**D30. Grounded answers: "answer ONLY from the records, say so if missing, cite ids".** Verified: "How much did I spend in Japan?" returned "I do not have that information".

**D31. Search service in `northeurope`, not `swedencentral`.** swedencentral returned `InsufficientResourcesAvailable` (Azure capacity, not quota). Search does not have to share a region with Foundry here because the client embeds the text and calls each service separately. Trade-off: a few ms of latency and an exception to D3. *Change when:* data residency rules or integrated vectorization (service-to-service calls) require co-location.

**D32. Separate embeddings client on the resource-level endpoint.** The project-scoped endpoint behind `get_openai_client()` returns an empty `404` for `/embeddings`; `get_embeddings_client()` uses `<resource>/openai/v1/` with a keyless token provider, built from the same `FOUNDRY_PROJECT_ENDPOINT`.

### Lessons from the Lab 3 run
- A resource provider must be registered once per subscription (`Microsoft.Search`); the CLI did it automatically.
- `InsufficientResourcesAvailable` means regional capacity, not quota: try another region.
- SKU = the pricing/capability tier: `--sku` for Search, `--sku-name` / `--sku-capacity` for model deployments.
- `model=` takes the deployment name, never the model name (got it right in Lab 3 after missing it in Labs 1 and 2).
- An empty `404` on a path that exists elsewhere usually means the route is not served on that endpoint, not that the deployment is missing.
- Top-k retrieval is incomplete by design: the food total was 140.3 instead of 152.8 because 2 of 6 food records were not retrieved, while the answer looked confident and showed its arithmetic. Totals, counts and averages belong in code or tools, not in the LLM; hand the model the computed number.
- Least privilege: the app that only queries needs Search Index Data Reader, not Contributor.

### Lab 2: Model selection and routing

**D15. Compare `gpt-4.1-mini` against `gpt-4o`**
- *Why:* `gpt-4.1` was the first choice but this subscription has 0 quota for it (`InsufficientQuota`). `gpt-4o` is a larger non-reasoning model with quota, so size is the main variable.
- *Alternative:* reasoning models (`o4-mini`, `gpt-5-mini`): hidden reasoning tokens muddy a first comparison.
- *Change when:* `gpt-4.1` quota is granted, or Lab 4 needs multi-step reasoning.

**D16. Decide with a labelled set, not by feel.** Measured: accuracy, latency, tokens, cost per model. Result: mini 11/12 vs gpt-4o 12/12; `gpt-4o` costs about 7.6x more per expense. With a one-line instruction ("if several parts, choose the primary purpose") mini reached 12/12 too, at the cost of about +36% tokens (501 -> 705 per 12 items).
- *Caveat:* the prompt was tuned on the same 12 items, so 12/12 is optimistic. Use held-out items before trusting it.

**D17. Include ambiguous rows.** Clear rows make every model look perfect; only the ambiguous row separated the models. Wrong answers on ambiguous input are also low-stakes because the user can correct the category.

**D18. Route by task: `categorize` -> mini, `advise` -> gpt-4o.** Cost follows volume. Static task routing is the right tool when the task is known in advance; the alternatives are a per-agent model (Lab 4), the Foundry `model-router` deployment (dynamic, for unpredictable prompts) and an API Management gateway (fallback, load balancing, Lab 6).

**D19. Router config from env vars.** Swapping a model is a config change, not a code change.

**D20. Second deployment is `Standard` (regional), capacity 10.** Quota is per model AND per deployment type: `Standard.gpt-4o` had 50, GlobalStandard had none. Regional costs about 21% more than global but keeps processing in Sweden.

**D21. Prices from the Azure Retail Prices API** (`https://prices.azure.com/api/retail/prices`, no login). The Foundry compare page's "Estimated cost" is a benchmark index, not dollars. Prices used: mini global $0.40 in / $1.60 out per 1M; gpt-4o regional $3.025 / $12.10.

### Lessons from the Lab 2 run
- `InsufficientQuota` with `0 / 0` means the limit is zero, not exhausted; lowering capacity does not help. Find usable quota with `az cognitiveservices usage list -l <region> -o json` (the table view hides names).
- Quota is per subscription, region, model and deployment type. 1 capacity unit on GlobalStandard/Standard = 1K tokens per minute.
- `model=` takes the **deployment name** (missed in Lab 1 and again in Lab 2).
- A 429 at capacity 10 means the TPM cap is exceeded: retry with backoff, raise capacity if quota allows, or spread across deployments. A gateway is one option, not the reading of the number.
- Tuning a prompt on the eval set contaminates the eval set; keep held-out items.

### Lessons from the Lab 1 run (so we don't repeat them)
- The CLI `--name` is the **Foundry resource**, not the project.
- The role "Azure AI User" is now called **Foundry User**; other roles were renamed too (Foundry Project Manager, Foundry Account Owner).
- Lab scripts run from the project root as modules: `python -m app.ai.lab01_smoke_test`.
- The venv must be active in every new terminal: `source .venv/bin/activate`.
- `.gitignore` already covered `.env` and `.venv`; appending without a trailing newline merged entries.

## 4. Lab format (every lab must follow this)

1. **Spec first:** goal, requirements, constraints, and a decision table (each choice with *why* and the alternative rejected).
2. **Prerequisites** and **cost/resource warning** (what bills, estimate, cleanup, guardrails).
3. **Hybrid tasks**, each with Objective, Why this approach, Steps (UI/portal and CLI/code), Code with explanations, Expected output, Common errors.
4. **Verification** in the UI.
5. **Self-check** (exam style) and a **decision recap** at the end.
6. Update this file: decision log entries and lessons.

## 5. Status

| Lab | State |
|---|---|
| 1 Foundation | Done; self-check 2.5/4 (missed: `model=` is the deployment name; weak on the reasons for keyless auth) |
| 3 Grounding (AI Search) | Done 2026-11-03, see `plans/lab-03-grounding.md`; self-check 4.5/6 (missed: least-privilege role is Index Data Reader; aggregation belongs in code, not the LLM) |
| 4 Advisor agent | Next (tools for aggregation, knowledge = this index, memory) |
| 2 Model selection and routing | Done (committed 74bb336); run complete 2026-11-03; self-check 3.5/5 (missed: `model=` is the deployment name again; meaning of 429 at capacity 10). Pending: Monitor tab check |

Theory source: Udemy "Microsoft AI-103: Azure AI Apps and Agents Developer Course". Workflow: finish a course section, then do its labs here.
- Section 2 (Choose Services and Set Up Foundry): theory covered 2026-11-02, maps to Labs 1-5. Section 2 quiz: not logged yet.
- Section 3 (Manage, Monitor, and Secure): not started, maps to Lab 6 and part of 7. Quotas/429s, cost, monitoring, keyless/managed identity, private networking.
