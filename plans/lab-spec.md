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

### Lab 6: Ops (quotas, cost, monitoring, identity, networking)

Full table with rejected alternatives and change triggers: `plans/lab-06-ops.md`. What was built and measured:

**D57. Retry on 429 and timeouts with exponential backoff and full jitter, honour `Retry-After`.** `app/ai/resilience.py`: 4 attempts per deployment, base 1 s, cap 20 s, total budget 45 s; client timeout 30 s with no SDK retries (`max_retries=0`) so one layer owns retrying. Verified: raw burst of 120 calls gave 113 x 429; with retry and failover 30/30 succeeded. Offline tests with a fake clock (8 tests) and a mutation check.

**D58. Fail over to a second deployment after retries are exhausted.** `FOUNDRY_FALLBACK_<TASK>` env vars. Quota is per deployment, so a second deployment is a second pool of capacity; a retry alone cannot create capacity. The advisor agent path still has no retry or failover (open).

**D59. Capacity stays at 10; bursts are absorbed in code.** Capacity is the spend-speed brake (D6).

**D60. Usage and cost logged per call in our own code** (`app/ai/usage.py`, JSON lines: task, deployment, tokens, latency, cost). Validated against the Azure Monitor metrics and the Foundry Traces page. Prices by model-name prefix.

**D61. Daily token cap enforced before each call** (200,000 tokens, in memory, resets on restart). It bounds total spend only for calls that go through our code; capacity bounds speed, `max_output_tokens` bounds one response, the retry cap bounds retry amplification. None of them is a budget.

**D62. OpenTelemetry to Application Insights (workspace-based).** `app/ai/telemetry.py`: `configure_azure_monitor(logger_name=..., sampling_ratio=1.0)` plus the Foundry SDK instrumentor. Connection string read from the project connection, not copied into `.env`. Workspace, Application Insights and the project connection are now in `infra/main.bicep` behind `deployMonitoring` (compiled; `what-if` not run against `rg-expense-ai`).

**D63. Prompt and response content is not recorded in traces** (`enable_content_recording=False`). Expense data is personal data. Verified 2026-11-12: no prompt or answer text appears in `customDimensions`.

**D64. Index health = live document count against the source + golden queries (hit@5).** `lab06_index_health.py`, golden cases matched by description because ids are record hashes (D29). Verified: PASS, and a deliberate delete gave a count FAIL. Count uses `get_document_count()`; `get_index_statistics` lags minutes.

**D65. Keyless enforced, not only practised, plus a user-assigned runtime identity.** `disableLocalAuth` was `null` on the live Foundry resource and `false` (`aadOrApiKey`) on Search: the hand-made resources had drifted from the Bicep. Fixed both live and in `main.bicep` (Search rejects `authOptions` together with `disableLocalAuth`). `id-expense-advisor-app` holds exactly two roles: Foundry User on the project and Search Index Data Reader on the service (in `rebuild.sh`, human-run).

**D66. Roles at the narrowest scope.** Removed from the developer account: the redundant Search Index Data Reader, the subscription-wide Foundry User and the leftover role on an unused portal-created group. Left open: Owner at the subscription (acceptable on a personal trial, first thing to narrow in a work account). The project-scoped runtime role was not tested end to end (no host).

**D67. Private endpoint and public access disabled, proved in a throwaway group.** `infra/network-test.bicep`: account, VNet and subnet, private endpoint, three `privatelink` DNS zones with VNet links, zone group. Verified: with the endpoint present, `nslookup` showed the `privatelink` CNAME but still a public IP from outside the VNet; with public access disabled the same call that returned a model list returned `403 Public access is disabled. Please configure private endpoint.` Group deleted and account purged.

### Lessons from the Lab 6 run
- A retry cannot create capacity: it only waits for a window. Failover to a second deployment adds capacity. Patience is capped by attempts before it is capped by the time budget (about 7 s per deployment here), so predict from the binding limit.
- Timeouts are a second failure mode: the service may queue instead of answering 429, and a timed-out request can still complete and bill server-side. Set a client timeout and retry it.
- Azure Monitor's default sampler is rate-limited (5 traces per second); in a tight loop it drops spans and the Foundry SDK instrumentor then crashes on a non-recording span. Use `sampling_ratio=1.0` while volume is small.
- App Insights Logs uses classic table names (`traces`, `dependencies`, `requests`; `timestamp`, `message`, `customDimensions`); the Log Analytics workspace uses `AppTraces`, `AppDependencies`. The KQL editor runs only the query at the cursor.
- Metrics splitting needs one metric per chart. Azure OpenAI Requests and Processed Inference Tokens split by `ModelDeploymentName` or `StatusCode`.
- Alert "Threshold Sensitivity" (dynamic thresholds: High = tighter band, more alerts) is not the content-filter severity threshold (Low = strictest). Opposite directions, classic exam trap.
- Hierarchy: subscription, resource group, Foundry resource (deployments, keys, roles, networking), Foundry projects (agents, files, connections). The portal form creates a new resource; the API or Bicep creates a child project.
- After creating and deleting a second project the agent's Entra identity was disabled (cause unproven); the Enable button did nothing; deleting and recreating the agent from code fixed it.
- The `expenses` search index vanished unexpectedly (found by the agent answering "data issue"); `lab03_build_index` restored it. This is the case the health check exists for.
- `get_index_statistics` and the portal document count lag minutes behind uploads and deletes; "Uploaded N/N" only means accepted. Use a live count query.
- Usage log lines are written after the span ends, so they carry no trace id (matters for Lab 8).
- `DefaultAzureCredential` tries the managed-identity endpoint first on a laptop (504 noise in dependencies).
- `az` prints nothing for a `null` property and for a successful delete; `az resource update` prints the whole resource.
- A user-assigned managed identity is a standalone resource with its own lifecycle; attach it to the host that runs the code, not to the Foundry project. The CLI role listing shows its `clientId`, while `principalId` is what role assignments use.
- Role propagation can take minutes and shows as `Principal does not have access to API/Operation`; the real network denial is `403 Public access is disabled`. Do not read a generic permission error as a network block.
- Each Azure resource type has its own API version list: `privateDnsZones@2024-05-01` has no types, `@2024-06-01` does; `privateDnsZoneGroups` follows the `Microsoft.Network` versions. Bicep `parent:` needs a resource reference, not `.name`, and looped children are indexed by position, not by value.
- The `privatelink.*` DNS zone names are dictated by the CNAME Azure inserts once a private endpoint exists, not a free naming convention; one missing or unlinked zone means the app silently keeps using the public IP.
- Private endpoints close only the data plane; ARM and the portal still work, so developers keep deploying but need VPN, ExpressRoute, zero-trust access, a jump host or an in-VNet runner to call the data plane.
- DNS broke at home but not at the office with no Azure change: the long CNAME chain failed on the router's resolver; `1.1.1.1` worked.
- The live deployments in `rg-expense-ai` still auto-upgrade model versions (`OnceNewDefaultVersionAvailable`), the same drift Lab 5 found in the test group; the hand-made environment never got D54 until the template is deployed there. A model version can therefore change without a code change.
- A hand-made PUT is not proof of state: the connection was sent `isSharedToAll: true` and reads back `false`. Read back what the service reports before copying it into a template.
- Self-check misses: why the `privatelink` DNS zone, not disabling public access, fixes a public IP (missed twice); which cost controls bound what (rate versus total versus one call); jitter prevents synchronized retries; data-layer checks are count parity, golden queries and freshness.

### Lab 7: Guardrails and evaluation (as built, 2026-11-17)

**D68. Custom RAI policy in Bicep (`expense-advisor-policy`, based on `Microsoft.DefaultV2`), attached to the chat deployments only.** Embeddings keep the default policy. The project must be written first (`dependsOn: [project]`) because the Cognitive Services account accepts one write at a time (`RequestConflict` otherwise). The base policy did not carry the Protected Material filters, so both are declared explicitly (text blocking, code annotate-only).

**D69. Harm thresholds per category, self-harm strictest.** In the API `Low` is the strictest setting (the portal calls it "Highest blocking"); Block means the request fails, Annotate only reports.

**D70. Jailbreak shield on the prompt, indirect-attack shield declared on the prompt source.** Measured result: the jailbreak shield caught the DAN persona and the role-play and override prompts, but not a weak "ignore your instructions" one (it is a classifier). The indirect-attack shield never fired in any placement (tool result, user message, with or without `"""`); cause unproven (the Responses API may not scan documents, or the classifier wants another format). Treat it as contributing nothing on this path until shown otherwise.

**D71. Block in production, annotate to tune.** Probe cases for benign, jailbreak, persona and harmful prompts are in `lab07_probe.py`; a blocked prompt is not retried.

**D72. Spotlighting, our own, on untrusted tool output only.** `search_expenses` output is wrapped `<<DATA>>"""..."""<</DATA>>` and the instructions say it is untrusted. The service's Spotlighting preview is chat-completions only; we use Responses. Three variants (unmarked, `"""`, full) on a poisoned index: the agent obeyed in none, so the effect of spotlighting is not separable from the model's own training (n=3). It is a second layer, not a proof. The layer to remove last is the read-only tool design (D37) plus approval (Lab 8).

**D73-D74. `safety.interpret` returns a typed `SafeResult`; user text is generic, details go to the usage log.** A 400 `content_filter` can come from the completion side (`source_type`); other `BadRequestError`s re-raise. `ask_safe` and `chat_safe` wrap the router and the agent; a blocked turn keeps the previous response id.

**D75. Fixed 15-row set, judge `gpt-4.1-mini`, not the advisor model.** Context is captured from the real tool outputs, ground truth is computed from the seed file. The judge is noisy: a rerun of identical text moved one row by 2 points. Compare only complete runs (a NaN is dropped from the mean, so an incomplete run averages different rows).

**D76. Groundedness and relevance run; safety evaluators and tool-call accuracy not run.** Safety evaluators are service-hosted and need project and region details that were not verified. Attack rows do not suit quality evaluators (a correct refusal scores relevance 1).

**D77. Red team: fallback script plus the managed Foundry run.** Fallback `lab07_redteam.py` (12 attacks, whole app): attack success rate **2/12**, both in prompt extraction (the French translation of the system prompt leaked; the tool names and parameters were listed). Jailbreaks 3/3 blocked by the shield; exfiltration, tool abuse and encoded attacks held by the model alone. Managed run: **0/114** for violence and self-harm (60 explicit refusals, some blocked by the filter), but the Sensitive data leakage category was configured and produced no results at all, so leakage is unmeasured there. The managed run cannot execute our local tools, so it tests the model, filter and instructions, not the app.

### Lessons from the Lab 7 run
- Removing the grounding sentence ("answer only from tool results") changed nothing measurable: 9 of 15 answers identical, the rest reworded, all three unanswerable questions still answered honestly. The instruction is cheap insurance, not a proven control. Test a control by removing it before claiming it.
- Built-in groundedness missed an invented currency symbol (`€` in one run, `£` in another, none in the data) and scored the worse one higher. Quality scores of 4-5 do not mean faithful; check the text.
- Neither the filter nor the shield covers prompt extraction or tool-schema disclosure; the plain request was refused, the same request as a translation worked. Assume the system prompt leaks and keep nothing sensitive in it.
- Instructions are a steering layer, not a security boundary: the refusal of "ignore your instructions" cannot be credited to the prompt alone (model training confounds it).
- A single obfuscation (Base64, reversed text) was handled by the model, not by the platform: one thin layer.
- `azure-ai-evaluation` 1.18.12 on Python 3.14: the library validator type-checks `credential: Any` with `isinstance` and fails; pass the credential to the evaluator constructors, not the model config. openai 3.x uses `httpx2`. Evaluators run 10 workers, so a capacity-10 judge produces 429s and NaN rows.
- The managed red team expands "5 seed queries" to 19 per technique, redacts the prompts in the results, and its wizard creates an evaluation definition that must be deleted separately from the run.
- Default-policy view in the portal and the policy in Bicep differ until the Protected Material filters are added explicitly.
- Scores: Groundedness, Relevance, Coherence and Fluency are 1-5 Likert scores, 5 best, default pass threshold 3. The safety evaluators (violence, self-harm, hate, sexual) are the opposite: 0-7 severity, lower is better.
- Self-check 8/8 (exam format).

## 4. Lab format (every lab must follow this)

1. **Spec first:** goal, requirements, constraints, and a decision table (each choice with *why* and the alternative rejected).
2. **Prerequisites** and **cost/resource warning** (what bills, estimate, cleanup, guardrails).
3. **Hybrid tasks**, each with Objective, Why this approach, Steps (UI/portal and CLI/code), Code with explanations, Expected output, Common errors.
4. **Verification** in the UI.
5. **Self-check** in exam format: multiple choice, exactly one correct answer, or "Choose two." when two are correct (never three), letters only. And a **decision recap** at the end.
6. Update this file: decision log entries and lessons.

## 5. Status

| Lab | State |
|---|---|
| 1 Foundation | Done; self-check 2.5/4 (missed: `model=` is the deployment name; weak on the reasons for keyless auth) |
| 2 Model selection and routing | Done (committed 74bb336); run complete 2026-11-03; self-check 3.5/5 (missed: `model=` is the deployment name again; meaning of 429 at capacity 10). Pending: Monitor tab check |
| 3 Grounding (AI Search) | Done 2026-11-03, see `plans/lab-03-grounding.md`; self-check 4.5/6 (missed: least-privilege role is Index Data Reader; aggregation belongs in code, not the LLM) |
| 4 Advisor agent | Done 2026-11-03, see `plans/lab-04-advisor-agent.md`; self-check 7/7, all tasks run (chat, tool calls, memory); Task 6 answered |
| 5 Delivery (IaC, CI/CD) | Done 2026-11-04, see `plans/lab-05-delivery.md`; D43-D56 logged; self-check 5/7 (partial: why the test env vars are safe, why the pipeline cannot create roles, soft-delete purge, why the credential is bound to an environment). Verified: 8 tests + mutation, Bicep deployed to `rg-expense-ai-test`, CI green, OIDC deploy green behind approval. Unverified: `rebuild.sh` with `work.bicepparam` in a new subscription. Cleanup pending |
| 6 Ops (quotas, cost, monitoring, managed identity, networking) | Done 2026-11-12, see `plans/lab-06-ops.md`; D57-D67 logged; all six tasks run (commits a3708be, 195180a, 58b3dc2, 0f9327a, cb36ffb, c9bf68c). Self-check 4.5/8 as open questions, then 2.5/4 in exam format (missed: private DNS zone twice, which cost controls bound what, jitter reason). 30 offline tests. `what-if` of `dev.bicepparam` against `rg-expense-ai` (2026-11-12): workspace and Application Insights unchanged; real drift found: live deployments use `OnceNewDefaultVersionAvailable` (auto-upgrade) while the template pins `NoAutoUpgrade` (D54), and the connection's `isSharedToAll` is false live. Fixed 2026-11-12: template deployed to `rg-expense-ai` (deployment `lab6-sync`), all three deployments now `NoAutoUpgrade`. The 429 alert rule is deleted; the only action group left is the automatic Application Insights Smart Detection one |
| 7 Guardrails and evaluation (content filters, Prompt Shields, evaluators, red teaming) | Done 2026-11-17, see `plans/lab-07-guardrails-evals.md`; D68-D77 logged as built. Tasks 1-5 run (policy deployed, safe-chat, injection table, evaluation A/A2/B, red team 2/12 local and 0/114 managed). Self-check 8/8. Open items: Foundry evaluation logging and safety evaluators unverified; indirect-attack shield silent (cause unproven). `expenses-attack` index deleted (confirmed) |
| 8 Audit and governance (traces, provenance, approvals, tool access) | Plan written 2026-11-09: `plans/lab-08-audit-governance.md`, D78-D88 proposed. Not started |

Theory source: Udemy "Microsoft AI-103: Azure AI Apps and Agents Developer Course". Workflow: finish a course section, then do its labs here.
- Section 2 (Choose Services and Set Up Foundry): theory covered 2026-11-02, maps to Labs 1-5. Section 2 quiz: not logged yet.
- Section 3 (Manage, Monitor, and Secure): theory covered, Lab 6 done 2026-11-12 (part of Lab 7 still to do). Quotas/429s, cost, monitoring, keyless/managed identity, private networking.
