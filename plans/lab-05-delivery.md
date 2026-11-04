# Lab 5: Delivery (tests, Bicep, CI/CD, environment config)

Builds on Labs 1-4 (see `plans/lab-spec.md`). Theory: Section 2 (integrate with CI/CD, infrastructure as code).

## 1. Spec

**Goal.** Everything built by hand in Labs 1-4 (portal clicks and `az` commands) becomes **repeatable and reviewable**: tests that run without Azure, infrastructure described as code, and a pipeline that checks every change and deploys infrastructure without any stored secret.

**Requirements**
1. A reproducible Python environment (pinned dependencies, runtime vs dev split). Today `requirements-ai.txt` is missing `azure-search-documents`, so a clean install would break the Lab 3 imports.
2. Unit tests for the AI layer that **never call Azure** (design principle 5), including a test that encodes "the agent has no write tools" (D37).
3. A Bicep template describing the Foundry resource, project, model deployments and (optionally) the Search service, with one parameter file per environment.
4. A **CI** workflow on every pull request: install, run tests, compile the Bicep.
5. A **CD** workflow that previews (`what-if`) and deploys the Bicep to a *test* resource group, authenticating with **OIDC federation** (no secret in GitHub), behind a human approval.
6. Environment configuration documented: where each value lives locally, in CI and in Azure.

**Constraints.** Never deploy over the hand-made `rg-expense-ai` (it is only compared with `what-if`). Cheapest thing that works, tokens-only cost, one-command cleanup, nothing secret in git. You run every command; I only write code.

### Decision table

| # | Decision | Why | Rejected alternative | Change when |
|---|---|---|---|---|
| D43 | **Bicep** for infrastructure | Native to Azure, supports new resource types early, compiles to ARM, has `what-if` and no state file to manage | Terraform: better for multi-cloud, but adds a state backend. ARM JSON: same engine, unreadable. Portal/CLI scripts: no preview, no drift detection | The team standardizes on Terraform or spans clouds |
| D44 | One resource group per environment, one parameter file per environment (`dev`, `test`) | This is the D2 "change when" trigger. Same template, different parameters, so environments cannot drift apart by hand | One shared group; copy-pasted templates | Never |
| D45 | `disableLocalAuth: true` on the AI account | Turns D8 (keyless) from a habit into a **platform rule**: API keys cannot be used even if someone creates one | Leaving keys enabled "just in case" | A tool only supports keys |
| D46 | Model deployments as an array parameter, created **one at a time** (`@batchSize(1)`) | The service rejects concurrent deployment operations on one account; the array lets each environment choose its models and capacity | Hardcoded deployments; parallel creation | Never |
| D47 | Search behind `deploySearch` and its own `searchLocation` | Only **one Free** search service per subscription (D22) and capacity can run out per region (D31): the template must let you skip it or place it elsewhere | Always deploying it | A paid tier is used per environment |
| D48 | **Role assignments are not in the pipeline** | A pipeline identity that can grant roles can grant itself Owner. Keep RBAC changes human-run (or a separate, tightly scoped, approved process) | Putting `Microsoft.Authorization/roleAssignments` in the template and giving the pipeline User Access Administrator | A mature RBAC process with constrained delegation exists |
| D49 | CI uses **no Azure access** | Tests use stubs, so CI is fast, free, safe for pull requests from anyone, and proves the core still runs without Azure | Running tests against real Foundry | Evaluation runs (Lab 7) are added as a separate, approved job |
| D50 | **OIDC federation** instead of a client secret | GitHub proves its identity with a short-lived token; Azure trusts it only for this repo and environment. Nothing to leak, rotate or expire | A service principal secret stored in GitHub secrets | Never for Azure deployments from GitHub |
| D51 | Federated credential bound to the GitHub **environment** `test`, with a required reviewer | Only runs in that environment can obtain a token, and a human must approve it (the Lab 4 lesson: dangerous actions need approval) | Binding to a branch only: any workflow on `main` could deploy | Production gets its own environment, identity and reviewers |
| D52 | Pipeline identity gets **Contributor on the test resource group only** | Least privilege: it can touch one group and cannot grant roles | Contributor on the subscription | Never |
| D53 | Pin dependencies (`requirements-ai.txt`, `requirements-dev.txt`) and pin GitHub Actions to a major version (a commit SHA is stronger) | Reproducible builds; a moving tag is a supply-chain risk | Unpinned installs, `@main` actions | A dependency-update bot is added |
| D54 | `versionUpgradeOption: NoAutoUpgrade` on every deployment | Found by `what-if`: the live deployments auto-upgrade to new default model versions, which breaks the reproducibility D7 wanted (a silent model change can alter categorization results) | The default `OnceNewDefaultVersionAvailable`: convenient, but unannounced behavior changes | Never in production; you must then upgrade by hand before a model's retirement date |
| D55 | State `raiPolicyName` in the template | The content filter policy is part of the environment's specification; today it is only an implicit default, and Lab 7 will change it | Leaving it implicit | Never |

## 2. Prerequisites and cost

- Labs 1-4 done, venv active, `az login` active, the GitHub remote works (`git@github-personal:vasildimov98/expense-tracker.git`).
- Azure CLI with Bicep (`az bicep version`; `az bicep install` if missing).
- **Cost:** the AI account itself has no standing charge, model deployments only bill tokens, and nothing in the test environment calls a model. The test environment skips Search (the one free slot is already used). GitHub Actions on a private repo has a free monthly allowance, far above this lab.
- **Quota:** the test environment deploys **one** small embedding deployment (capacity 1) so it does not compete with your 10-unit deployments.
- **Cleanup (end of lab):** delete the test resource group **and purge** the soft-deleted AI account, then optionally delete the app registration. Commands are in section 7.
- **What I have not verified:** the Bicep API versions and exact property names, because I cannot run Azure here. Task 3 makes **you** validate them with `az bicep build` and `what-if` before anything is deployed. Treat a warning or error there as the lab working, and paste it to me.

## 3. Tasks

### Task 1: A reproducible environment and a small refactor

**Objective.** `pip install` from the repo alone gives a working environment, and the retrieval code stops living in a lab file.

**Why.** CI starts from an empty machine; anything that only works on your laptop fails there. This is also where the Lab 4 technical debt (`advisor_tools` importing a lab file) is paid.

1. Add the missing runtime dependency to `requirements-ai.txt` (keep it alphabetical):
   ```
   azure-search-documents==12.0.0
   ```
2. Create `requirements-dev.txt`:
   ```
   -r requirements-ai.txt
   pytest==<version>
   ```
   Get the version with `pip install pytest` then `pip freeze | grep -i -E "^(pytest|pluggy|iniconfig|packaging)"`. Pin pytest in this file; its helper packages can stay out (pip resolves them) or be pinned too.
3. Create `app/ai/retrieval.py` by **moving** `retrieve` out of `lab03_query.py`:

   ```python
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
   ```
   Then in `lab03_query.py` delete the function and the imports it no longer needs, and add `from app.ai.retrieval import retrieve`. In `advisor_tools.py` change `from app.ai.labs.lab03_query import retrieve` to `from app.ai.retrieval import retrieve`.
4. Check the install works from scratch (this catches missing pins): create a throwaway venv, `pip install -r requirements-dev.txt`, and `python -c "import app.ai.advisor_tools"` with dummy env vars (Task 2 shows the variables). Then delete the throwaway venv.

**Verify.** `python -m app.ai.labs.lab04_chat` still works with your real `.env` (this one *does* call Azure: your decision when to run it).

### Task 2: Tests that never call Azure

**Objective.** Fast tests for the deterministic parts: totals, argument validation, tool dispatch, routing, and the "no write tools" rule.

**Why.** The agent's behavior is model-dependent, but everything *around* it is plain code and can be tested in milliseconds. A test is also the cheapest permanent form of a decision: D37 becomes a failing build if someone adds `delete_expense`.

Create `pytest.ini` in the project root:

```ini
[pytest]
pythonpath = .
testpaths = tests
```

Create `tests/conftest.py`. Several modules read environment variables **at import time** (`foundry_client.DEPLOYMENT`, `search_client`), so dummy values must exist before the first import. `setdefault` plus the fact that `load_dotenv()` never overrides existing variables means tests use the dummies even on your laptop and can never reach your real endpoints:

```python
import os

# Dummy values so Azure-reading modules import. No test talks to Azure.
for key, value in {
    "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/test",
    "FOUNDRY_MODEL_DEPLOYMENT": "mini",
    "FOUNDRY_ADVISOR_DEPLOYMENT": "advisor",
    "FOUNDRY_EMBEDDING_DEPLOYMENT": "embed",
    "AZURE_SEARCH_ENDPOINT": "https://example.search.windows.net",
    "AZURE_SEARCH_INDEX": "expenses",
}.items():
    os.environ.setdefault(key, value)
```

Create `tests/test_advisor_tools.py`:

```python
import json

import pytest

from app.ai import advisor_tools


@pytest.fixture
def expenses_file(tmp_path, monkeypatch):
    path = tmp_path / "expenses.json"
    path.write_text(json.dumps([
        {"category": "Food", "amount": 10.25, "description": "lunch", "date": "2026-10-01"},
        {"category": "Food", "amount": 5.5, "description": "coffee", "date": "2026-10-02"},
        {"category": "Transport", "amount": 20.0, "description": "taxi", "date": "2026-10-03"},
    ]))
    monkeypatch.setattr(advisor_tools, "EXPENSES_PATH", str(path))


def test_summary_totals_are_exact(expenses_file):
    result = advisor_tools.get_spending_summary()
    assert result["total"] == 35.75
    assert result["per_category"] == {"Food": 15.75, "Transport": 20.0}
    assert result["largest_expense"]["description"] == "taxi"


def test_search_returns_only_needed_fields(monkeypatch):
    raw = [{"id": "abc", "description": "x", "category": "Food", "amount": 1.0,
            "date": "2026-10-01", "@search.score": 0.1}]
    monkeypatch.setattr(advisor_tools, "retrieve", lambda query, k, odata_filter: raw)
    assert advisor_tools.search_expenses("x") == [
        {"description": "x", "category": "Food", "amount": 1.0, "date": "2026-10-01"}
    ]


def test_search_builds_filter_from_validated_category(monkeypatch):
    seen = {}

    def fake(query, k, odata_filter):
        seen["filter"] = odata_filter
        return []

    monkeypatch.setattr(advisor_tools, "retrieve", fake)
    advisor_tools.search_expenses("x", "Food")
    assert seen["filter"] == "category eq 'Food'"


def test_injected_category_is_rejected_before_searching(monkeypatch):
    monkeypatch.setattr(advisor_tools, "retrieve",
                        lambda *a, **k: pytest.fail("must not search"))
    evil = "Food' or amount gt 0 or category eq 'Food"
    out = json.loads(advisor_tools.run_tool(
        "search_expenses", json.dumps({"query": "x", "category": evil})))
    assert "error" in out


def test_unknown_tool_returns_error_json():
    out = json.loads(advisor_tools.run_tool("delete_expense", "{}"))
    assert "error" in out


def test_agent_has_no_write_tools():
    # D37 as a regression test: the agent may only read.
    names = [tool.name for tool in advisor_tools.TOOLS]
    assert not [n for n in names if n.startswith(("add", "delete", "update", "remove"))]
```

Create `tests/test_model_router.py`:

```python
import pytest

from app.ai import model_router


def test_route_reads_deployment_name_from_env(monkeypatch):
    monkeypatch.setenv("FOUNDRY_ADVISOR_DEPLOYMENT", "my-advisor")
    assert model_router.deployment_for("advise") == "my-advisor"


def test_unknown_task_raises():
    with pytest.raises(ValueError):
        model_router.deployment_for("translate")
```

Run: `python -m pytest -q`. Expected: all pass in well under a second. Then **break something on purpose** (change `round(summary.total, 2)` to `round(summary.total, 1)`) and confirm a test fails, then revert. A test you have never seen fail proves nothing. The test data uses `10.25` on purpose: with only one-decimal amounts, rounding to 1 or 2 digits gives the same result and this change would pass unnoticed (it did, in the first run of this lab). A test only protects what its data can distinguish.

**Common errors:** `KeyError: FOUNDRY_...` at import (conftest not picked up: check `pytest.ini` and that you run from the project root); `ModuleNotFoundError: app` (missing `pythonpath = .`); a test that hangs or hits the network (a function was not monkeypatched: the stub must replace the name *where it is used*, `advisor_tools.retrieve`, not where it is defined).

### Task 3: Infrastructure as code (Bicep)

**Objective.** One template, two environments, validated before any deployment.

**Why.** The template is the specification you wrote in `lab-spec.md` in executable form: region, SKU, capacity and version live in parameters, not in someone's memory. `what-if` is the safety net: it shows the exact create/modify/delete plan before anything changes.

Create `infra/main.bicep`:

```bicep
targetScope = 'resourceGroup'

@description('Globally unique; becomes <name>.cognitiveservices.azure.com and <name>.services.ai.azure.com')
param accountName string
param projectName string = 'expense-advisor'
param location string = resourceGroup().location

@description('Model deployments, created one at a time (D46).')
param deployments array = []

@description('Free tier allows one search service per subscription (D47).')
param deploySearch bool = false
param searchName string = ''
param searchLocation string = location

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: accountName
    allowProjectManagement: true
    publicNetworkAccess: 'Enabled'
    disableLocalAuth: true          // D45: keyless is enforced, not just practiced
  }
}

resource project 'Microsoft.CognitiveServices/accounts/projects@2025-06-01' = {
  parent: account
  name: projectName
  location: location
  identity: { type: 'SystemAssigned' }
  properties: {
    displayName: projectName
    description: 'Expense Advisor project'
  }
}

@batchSize(1)
resource modelDeployments 'Microsoft.CognitiveServices/accounts/deployments@2025-06-01' = [for d in deployments: {
  parent: account
  dependsOn: [ project ]            // the project updates the account: deployments must wait for it
  name: d.name                       // the deployment NAME your code passes as model=
  sku: { name: d.sku, capacity: d.capacity }
  properties: {
    model: { format: 'OpenAI', name: d.model, version: d.version }
    versionUpgradeOption: 'NoAutoUpgrade'   // D7 made real: no silent model changes
    raiPolicyName: 'Microsoft.DefaultV2'    // content filter policy, explicit (Lab 7 changes it)
  }
}]

resource search 'Microsoft.Search/searchServices@2025-05-01' = if (deploySearch) {
  name: searchName
  location: searchLocation
  sku: { name: 'free' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    authOptions: { aadOrApiKey: { aadAuthFailureMode: 'http401WithBearerChallenge' } }
  }
}

output projectEndpoint string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}'
output searchEndpoint string = deploySearch ? 'https://${searchName}.search.windows.net' : ''
```

Create `infra/dev.bicepparam` (documents the environment you built by hand; **only ever used with `what-if`**):

```bicep
using 'main.bicep'

param accountName = 'expense-advisor-resource'
param location = 'swedencentral'
param deploySearch = true
param searchName = 'srch-expense-advisor-vd91'
param searchLocation = 'northeurope'
param deployments = [
  { name: 'gpt-4.1-mini', model: 'gpt-4.1-mini', version: '2025-04-14', sku: 'GlobalStandard', capacity: 10 }
  { name: 'gpt-4o', model: 'gpt-4o', version: '2024-11-20', sku: 'Standard', capacity: 10 }
  { name: 'text-embedding-3-small', model: 'text-embedding-3-small', version: '1', sku: 'GlobalStandard', capacity: 10 }
]
```

Create `infra/test.bicepparam` (a tiny throwaway environment):

```bicep
using 'main.bicep'

param accountName = 'expense-advisor-test-vd91'
param location = 'swedencentral'
param deploySearch = false
param deployments = [
  { name: 'text-embedding-3-small', model: 'text-embedding-3-small', version: '1', sku: 'GlobalStandard', capacity: 1 }
]
```

Validate step by step (each is free):

```bash
# 1. Compile locally. Errors and warnings about API versions or property names show up here.
az bicep build --file infra/main.bicep --stdout > /dev/null

# 2. If a resource-type API version is flagged, list the valid ones:
az provider show --namespace Microsoft.CognitiveServices \
  --query "resourceTypes[?resourceType=='accounts/projects'].apiVersions[]" -o tsv

# 3. Drift check against what you built by hand (reads only, deploys NOTHING):
az deployment group what-if -g rg-expense-ai -p infra/dev.bicepparam
```

**Read the `what-if` output carefully.** Expect differences: the existing account has API keys enabled (`disableLocalAuth` would be `Modify`), and some properties will show noise. That is **drift**: what the template says versus what clicking produced. For every `Modify`/`Create` line decide whether the template or the portal is right. Do **not** run `az deployment group create` against `rg-expense-ai` (D44).

Then create the test group, preview and deploy there:

```bash
az group create -n rg-expense-ai-test -l swedencentral
az deployment group what-if -g rg-expense-ai-test -p infra/test.bicepparam
az deployment group create  -g rg-expense-ai-test -p infra/test.bicepparam
```

**Expected.** `provisioningState: Succeeded`, outputs with the project endpoint.

**Verify (UI).** Azure portal -> `rg-expense-ai-test` -> Deployments (the deployment history) and the AI resource. Check **Keys and endpoint**: local authentication is disabled, which is D45 working.

**Reading `what-if` (from the first run against `rg-expense-ai`):** a `-` line on a property your template does not mention is almost always a read-only or default value filled in by Azure (`currentCapacity`, `endpoints`, `internalId`, `computeType`...) and is **noise**: incremental mode does not delete it. A `+` or `~` on a property your template sets is a **real** change. The run showed one real change (`disableLocalAuth: true` on the account) and one real finding: the live deployments had `versionUpgradeOption: OnceNewDefaultVersionAvailable`, so the model version pinned in D7 was **not actually pinned**: Azure upgrades automatically when a new default version appears. The template now sets `NoAutoUpgrade` (D54) and states the content filter policy explicitly (D55).

**Lesson from the first real deployment:** `RequestConflict: Another operation is in progress on the resource ...accounts/<name>`. The project and the model deployments are both children of the account, so Bicep created them in parallel, and creating the project updates the account. `@batchSize(1)` only orders the deployments among themselves; the deployments need `dependsOn: [ project ]`. A template can compile and pass `what-if` and still fail on ordering: only a real deployment proves it. (Also: pressing keys in the terminal during `az deployment group create` cancels the CLI's wait, not the deployment; check `az deployment group list` for the state.)

**Lesson from the run:** `az bicep build` caught a casing mistake in the first draft (`hostingMode: 'default'` must be `'Default'`; the line was removed because it is the default). The API versions used here compiled without warnings.

**Common errors:** `InvalidApiVersionParameter`/`NoRegisteredProviderFound` (use the version list above, or register the provider); `InsufficientQuota` (lower the test capacity or pick another type, as in Lab 2); name already in use or `FlagMustBeSetForRestore` (a soft-deleted account holds the name: purge it, see cleanup); a deployment fails with a conflict (that is why `@batchSize(1)` exists: do not remove it).

### Task 4: CI workflow (every pull request)

**Objective.** A pull request cannot merge with failing tests or a template that does not compile.

**Why.** CI needs no Azure credentials (D49), so it is safe for any change and any contributor. Permissions are the minimum (`contents: read`).

Create `.github/workflows/ci.yml`:

```yaml
name: ci

on:
  pull_request:
  push:
    branches: [main]

permissions:
  contents: read

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.14"
          cache: pip
          cache-dependency-path: requirements-dev.txt
      - run: pip install -r requirements-dev.txt
      - run: python -m pytest -q
      - name: Bicep compiles
        run: az bicep build --file infra/main.bicep --stdout > /dev/null
```

Commit on a branch, push, open a pull request, and watch the **Actions** tab. Expected: a green check. Then **make it fail on purpose** (the broken test from Task 2) in a throwaway commit and confirm the pull request shows a red cross, then fix it.

**Common errors:** a dependency fails to install on the runner (a platform-specific pin in your freeze output: that is exactly what CI is for, fix the pin); `python-version: "3.14"` not found (use the version your venv shows in `python --version`, minor series only); `az: command not found` (the Ubuntu runner has it; check the step name).

### Task 5: CD workflow with OIDC (no secrets)

**Objective.** A workflow that proves who it is to Azure with a short-lived token, previews, then deploys the **test** environment after a human approves.

**Why.** D50-D52. The trust is set up once in Azure: "tokens issued by GitHub for repo `vasildimov98/expense-tracker`, environment `test`, may act as this identity, which can change only `rg-expense-ai-test`". Nothing secret ever exists.

**A. Azure side** (you run it):

```bash
SUB=$(az account show --query id -o tsv)
APP_ID=$(az ad app create --display-name gh-expense-advisor-test --query appId -o tsv)
az ad sp create --id "$APP_ID"

az ad app federated-credential create --id "$APP_ID" --parameters '{
  "name": "github-env-test",
  "issuer": "https://token.actions.githubusercontent.com",
  "subject": "repo:vasildimov98/expense-tracker:environment:test",
  "audiences": ["api://AzureADTokenExchange"]
}'

az role assignment create --assignee "$APP_ID" --role Contributor \
  --scope "/subscriptions/$SUB/resourceGroups/rg-expense-ai-test"

echo "client-id: $APP_ID"; az account show --query "{tenant:tenantId, subscription:id}" -o json
```

If `az ad app create` is refused, your tenant restricts app registrations: tell me and we will choose another route. None of these three values is a secret.

**B. GitHub side** (browser): repository -> Settings -> **Environments** -> New environment `test` -> add yourself under **Required reviewers**. In the same environment add three **variables** (not secrets): `AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`.

**C. Workflow.** Create `.github/workflows/deploy-test.yml`:

```yaml
name: deploy-test

on:
  workflow_dispatch:
  push:
    branches: [main]
    paths: ["infra/**"]

permissions:
  id-token: write      # lets the job request an OIDC token
  contents: read

concurrency: deploy-test   # never two deployments at once

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment: test        # the federated credential only accepts this environment
    steps:
      - uses: actions/checkout@v4
      - uses: azure/login@v2
        with:
          client-id: ${{ vars.AZURE_CLIENT_ID }}
          tenant-id: ${{ vars.AZURE_TENANT_ID }}
          subscription-id: ${{ vars.AZURE_SUBSCRIPTION_ID }}
      - name: What-if
        run: az deployment group what-if -g rg-expense-ai-test -p infra/test.bicepparam
      - name: Deploy
        run: az deployment group create -g rg-expense-ai-test -p infra/test.bicepparam
```

Run it from Actions -> deploy-test -> **Run workflow**. Expected: the job pauses for your approval, then logs in without any secret, shows the `what-if` (mostly "no change", since Task 3 already deployed), and succeeds.

**Verify.** Azure portal -> `rg-expense-ai-test` -> Deployments shows a second deployment, initiated by the workflow identity. Entra ID -> App registrations -> your app -> Certificates & secrets: **empty**. That emptiness is the point.

**Common errors:** `AADSTS70021: No matching federated identity record` (the `subject` does not exactly match `repo:<owner>/<repo>:environment:test`: case and spelling matter, or the job has no `environment:` line); `AuthorizationFailed` on deploy (the role assignment is missing or not yet propagated: wait a few minutes); the job never starts (the approval is waiting in the Actions UI).

### Task 6: Environment configuration map

Write down (no code) where each value lives, and check your answer against this table:

| Value | Local | CI | Deployed environment |
|---|---|---|---|
| `FOUNDRY_PROJECT_ENDPOINT`, deployment names, search endpoint, index name | `.env` (gitignored), documented in `.env.example` | Not needed (tests use dummies) | App settings / environment variables set by the deploy |
| Azure identity | `az login` -> `DefaultAzureCredential` | OIDC token (federated credential) | Managed identity |
| API keys / secrets | none | none | none (D8, D45, D50) |

Notice the pattern: **the same code runs everywhere because identity is resolved by `DefaultAzureCredential` and configuration comes from the environment** (D12, D19).

### Task 7: Keep the rebuild path in sync (account switch)

**Objective.** The environment can be recreated in another subscription (the personal trial credit ends and the work account follows, around December) with one reviewed command instead of a hand-built sequence.

**Why.** Nothing carries over between subscriptions. `scripts/azure/rebuild.sh` already rebuilds Labs 1-4 with `az` commands; the Bicep template does the same job with a preview and without drift. Do this **after** the test deployment in Task 3 succeeded, so the template is verified, not assumed.

1. Create `infra/work.bicepparam`: a copy of `dev.bicepparam` with **new globally unique names** (`accountName`, `searchName`) and a region/SKU per that subscription's quota (re-check with `az cognitiveservices usage list -l <region> -o json`, Lab 2 lesson).
2. In `scripts/azure/rebuild.sh`, keep the steps that are not infrastructure-as-code (provider registration, resource group, **role assignments**, which stay human-run per D48, and the printed `.env` values) and replace the three sections "Foundry resource + project", "model deployments" and "Azure AI Search" with one call:
   ```bash
   az deployment group what-if -g "$RG" -p "infra/$ENV.bicepparam"
   az deployment group create  -g "$RG" -p "infra/$ENV.bicepparam" --query properties.outputs
   ```
3. Print the `.env` values from the deployment outputs (`projectEndpoint`, `searchEndpoint`) instead of rebuilding them from variables.
4. `teardown.sh` stays as is; remember the soft-deleted AI account must be purged before its name can be reused.

## 4. Verification (summary)

- `python -m pytest -q`: green, no network.
- Pull request: CI green, and red when you break a test.
- `what-if` against `rg-expense-ai`: you can explain every difference.
- `deploy-test`: waited for approval, logged in without a secret, deployment visible in the portal.
- App registration has no secrets; AI account has local auth disabled.

## 5. Self-check (exam style)

1. A GitHub workflow must deploy to Azure. Which is the most secure way to authenticate?
   A. A service principal secret in GitHub secrets  B. A storage-account key  C. OIDC workload identity federation  D. The deployer's personal password
2. What does `az deployment group what-if` do?
   A. Deploys and rolls back on failure  B. Previews which resources would be created, modified or deleted without changing anything  C. Validates only the syntax  D. Deletes resources not in the template
3. Why does the template set `disableLocalAuth: true`?
4. Your tests need `FOUNDRY_MODEL_DEPLOYMENT` at import time but must never call Azure. What is the right approach, and why can it not accidentally reach your real endpoint on your laptop?
5. Why is the pipeline identity not allowed to create role assignments?
6. After deleting `rg-expense-ai-test`, deploying the same account name fails. Why, and what is the fix?
7. Why is the federated credential tied to the GitHub environment `test` instead of only to the repository?

Send your answers and I will mark them.

## 6. Decision recap

Describe infrastructure in code and preview it before applying (D43-D44); enforce keyless on the platform (D45); keep dangerous powers away from the pipeline (D48, D52) and behind a human (D51); give CI no Azure access at all (D49); and remove every stored secret (D50). Reproducibility starts with pinned dependencies (D53).

## 7. Cleanup

```bash
az group delete -n rg-expense-ai-test --yes
# The AI account is soft-deleted and keeps its name and quota until purged:
az cognitiveservices account list-deleted -o table
az cognitiveservices account purge -n expense-advisor-test-vd91 -g rg-expense-ai-test -l swedencentral
# Optional: remove the pipeline identity
az ad app delete --id <APP_ID>
```

Then delete the `test` environment in GitHub if you no longer need it.

## 8. After the lab

Send me: pytest output (including the deliberate failure), the `what-if` against `rg-expense-ai` (what drifted and your judgment on it), the CI and deploy run results, and the self-check answers. I will log D43-D55 and the lessons in `plans/lab-spec.md` and commit.
