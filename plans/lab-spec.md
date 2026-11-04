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

### Lab 4: Advisor agent (tools, knowledge, memory)

**D33. Prompt agent in Foundry Agent Service (`agents.create_version`).** Model, instructions and tools are stored and versioned server-side; each `create_version` call with the same name makes the next version. *Alternative:* a plain `responses.create(tools=...)` script, or the client-side Microsoft Agent Framework.

**D34. Agent model = the `advise` route (`gpt-4o`).** Tool selection and synthesis are the reasoning-heavy part; volume is low. *Change when:* an evaluation shows mini is enough (Lab 7).

**D35. Totals through a function tool over existing app code (`ExpenseService.compute_summary`).** The model decides *when* to call, never *how to add*. Result: Food 152.80 (the figure Lab 3 got wrong as 140.3). *Alternative:* larger top-k, or LLM arithmetic.

**D36. Knowledge through a function tool that reuses the Lab 3 hybrid retrieval.** We embed queries client-side and the index has no vectorizer. *Alternative:* the built-in Azure AI Search tool (project connection, roles; not tested).

**D37. Read-only tools only.** A tool that does not exist cannot be abused through prompt injection; writes would need human approval (Lab 8).

**D38. Validate model-supplied arguments, return tool errors to the model as data.** `Category(category)` guards the filter string.

**D39. `MAX_TOOL_ROUNDS = 5`.** Bounds a runaway tool loop, which costs tokens.

**D40. Short-term state with `previous_response_id`, long-term with a memory store.** Verified: the budget told in conversation 1 was recalled in a new conversation 2.

**D41. Memory scope per user (`user-vd91`).** A real app uses the signed-in user (`{{$userId}}`).

**D42. Memory is preview and stores personal facts.** Decide retention (TTL, default never expires) and deletion (`delete_scope`) before production.

### Lab 5: Delivery (tests, Bicep, CI/CD)

Full table with rejected alternatives and change triggers: `plans/lab-05-delivery.md`.

**D43. Bicep for infrastructure.** Native, early support for new resource types, `what-if`, no state file. *Change when:* the team standardizes on Terraform or spans clouds.

**D44. One resource group and one parameter file per environment (`dev`, `test`, `work`).** Same template, different parameters, so environments cannot drift apart by hand.

**D45. `disableLocalAuth: true` on the AI account.** Keyless (D8) becomes a platform rule: keys cannot be used even if someone creates one.

**D46. Model deployments as an array parameter created one at a time (`@batchSize(1)`, `dependsOn` the project).** The service rejects concurrent operations on one account.

**D47. Search behind `deploySearch` with its own `searchLocation`.** One Free service per subscription (D22) and regional capacity limits (D31).

**D48. Role assignments are not in the pipeline.** A pipeline that can grant roles can grant itself Owner. RBAC stays human-run.

**D49. CI has no Azure access.** Tests use stubs: fast, free, safe for any pull request. Verified: green on a clean GitHub runner.

**D50. OIDC federation instead of a client secret.** Short-lived token issued by GitHub, trusted by Azure for one repo and environment. Nothing to leak or rotate.

**D51. Federated credential bound to the GitHub environment `test` with a required reviewer.** Only a run in that gated environment gets a token; a repo-wide or branch-only binding would let any workflow or PR obtain one.

**D52. Pipeline identity is Contributor on `rg-expense-ai-test` only.** It can deploy there and cannot grant roles or touch anything else.

**D53. Pinned dependencies and Actions pinned to a major version.** Reproducible builds; a SHA pin is stronger.

**D54. `versionUpgradeOption: NoAutoUpgrade`.** Found by `what-if`: live deployments auto-upgrade model versions, which silently changes behavior.

**D55. State `raiPolicyName` explicitly.** The content filter is part of the environment spec (Lab 7 will change it).

**D56. Rebuild path = Bicep + a thin script (`scripts/azure/rebuild.sh`, `infra/work.bicepparam`).** Names come from environment variables (`readEnvironmentVariable`, fails loudly if unset); the script keeps only providers, resource group, human-run roles and the printed `.env`, with a what-if and confirmation before deploying. *Change when:* a mature RBAC process lets a pipeline do the roles. Unverified until the first run in the work subscription.

### Lessons from the Lab 1 run (so we don't repeat them)
- The CLI `--name` is the **Foundry resource**, not the project.
- The role "Azure AI User" is now called **Foundry User**; other roles were renamed too (Foundry Project Manager, Foundry Account Owner).
- Lab scripts run from the project root as modules: `python -m app.ai.lab01_smoke_test`.
- The venv must be active in every new terminal: `source .venv/bin/activate`.
- `.gitignore` already covered `.env` and `.venv`; appending without a trailing newline merged entries.

### Lessons from the Lab 2 run
- `InsufficientQuota` with `0 / 0` means the limit is zero, not exhausted; lowering capacity does not help. Find usable quota with `az cognitiveservices usage list -l <region> -o json` (the table view hides names).
- Quota is per subscription, region, model and deployment type. 1 capacity unit on GlobalStandard/Standard = 1K tokens per minute.
- `model=` takes the **deployment name** (missed in Lab 1 and again in Lab 2).
- A 429 at capacity 10 means the TPM cap is exceeded: retry with backoff, raise capacity if quota allows, or spread across deployments. A gateway is one option, not the reading of the number.
- Tuning a prompt on the eval set contaminates the eval set; keep held-out items.

### Lessons from the Lab 3 run
- A resource provider must be registered once per subscription (`Microsoft.Search`); the CLI did it automatically.
- `InsufficientResourcesAvailable` means regional capacity, not quota: try another region.
- SKU = the pricing/capability tier: `--sku` for Search, `--sku-name` / `--sku-capacity` for model deployments.
- `model=` takes the deployment name, never the model name (got it right in Lab 3 after missing it in Labs 1 and 2).
- An empty `404` on a path that exists elsewhere usually means the route is not served on that endpoint, not that the deployment is missing.
- Top-k retrieval is incomplete by design: the food total was 140.3 instead of 152.8 because 2 of 6 food records were not retrieved, while the answer looked confident and showed its arithmetic. Totals, counts and averages belong in code or tools, not in the LLM; hand the model the computed number.
- Least privilege: the app that only queries needs Search Index Data Reader, not Contributor.

### Lessons from the Lab 4 run
- A function tool is executed by YOUR process: the model returns a `function_call`, your code runs it and replies with a `function_call_output` using the same `call_id`. The Foundry playground can show the call but cannot run your local function.
- Observed: totals triggered `get_spending_summary` once; the follow-ups ("transport", "largest") made **no** tool call because the thread already held the result (saves calls, but can go stale if data changes mid-conversation).
- Tool output hygiene: the raw Search result included `@search.*` metadata (about 900 characters per lookup, resent as input tokens every turn). Return only the fields the model needs.
- A vector or hybrid lookup for "Japan" returned 5 unrelated records (always k results); the agent correctly judged none mentioned Japan. Relevance judgment was left to the model; a score threshold would make it explicit.
- Instructions are a steering layer, not a security boundary. The reliable defence is the capability being absent (read-only tools) or behind human approval. Injected text can also arrive through retrieved data, not only the user message.
- Memory extraction is asynchronous (`update_delay`, 300 s by default), so a fact is not instantly available.
- Debug prints of raw tool outputs expose data: remove them or move to logging (Lab 6).

### Lessons from the Lab 5 run
- A test that passes when the code is broken is worthless: with amounts that were already round, the rounding test could not detect a removed `round()`. Change the code on purpose (mutation check) and make the test data (10.25, 5.5) make the change visible.
- `pytest.ini` (`pythonpath`, `testpaths`) makes imports work; `conftest.py` is found automatically and sets dummy env vars with `setdefault` before the app modules import, so tests never need a real `.env`.
- `what-if` lists many `-` lines for properties the template does not set (Azure fills them in): read the `+` and `~` lines on properties you do set. Its real catch here was the auto-upgrade of model versions (D54).
- `RequestConflict`: project and deployments created in parallel on one account. Fix with `dependsOn`. Typing in the terminal cancelled the CLI wait but the deployment kept running; check with `az deployment group list`.
- Bicep: `hostingMode: 'default'` triggered warning BCP036 (the value is `Default`); removing the line uses the default.
- Deleted AI accounts are soft-deleted and keep their name until purged: delete the group, then `az cognitiveservices account purge`.
- OIDC login failed twice, both configuration: (1) the subscription ID was pasted into `AZURE_TENANT_ID` (both are GUIDs; error `invalid_tenant`); take both from `az account show`. (2) GitHub now issues ID-based subjects (`repo:owner@id/repo@id:environment:test`), so the credential with the plain subject gave AADSTS700213. A federated credential is an exact match on issuer, subject and audience: compare the "Federated token details" in the login log with the stored credential.
- A successful what-if against an already deployed template shows only noise, which is the proof that template and environment agree.
- `workflow_dispatch` ("Run workflow") only appears once the workflow file is on the default branch, so commit and push first.

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
| 2 Model selection and routing | Done (committed 74bb336); run complete 2026-11-03; self-check 3.5/5 (missed: `model=` is the deployment name again; meaning of 429 at capacity 10). Pending: Monitor tab check |
| 3 Grounding (AI Search) | Done 2026-11-03, see `plans/lab-03-grounding.md`; self-check 4.5/6 (missed: least-privilege role is Index Data Reader; aggregation belongs in code, not the LLM) |
| 4 Advisor agent | Done 2026-11-03, see `plans/lab-04-advisor-agent.md`; self-check 7/7, all tasks run (chat, tool calls, memory); Task 6 answered |
| 5 Delivery (IaC, CI/CD) | Done 2026-11-04, see `plans/lab-05-delivery.md`; D43-D56 logged; self-check 5/7 (partial: why the test env vars are safe, why the pipeline cannot create roles, soft-delete purge, why the credential is bound to an environment). Verified: 8 tests + mutation, Bicep deployed to `rg-expense-ai-test`, CI green, OIDC deploy green behind approval. Unverified: `rebuild.sh` with `work.bicepparam` in a new subscription. Cleanup pending |
| 6 Ops (quotas, cost, monitoring, managed identity, networking) | Waits for course Section 3 theory |
| 7-8 Safety (content filters, evaluators, tracing, tool-access control) | Wait for theory |

Theory source: Udemy "Microsoft AI-103: Azure AI Apps and Agents Developer Course". Workflow: finish a course section, then do its labs here.
- Section 2 (Choose Services and Set Up Foundry): theory covered 2026-11-02, maps to Labs 1-5. Section 2 quiz: not logged yet.
- Section 3 (Manage, Monitor, and Secure): not started, maps to Lab 6 and part of 7. Quotas/429s, cost, monitoring, keyless/managed identity, private networking.
