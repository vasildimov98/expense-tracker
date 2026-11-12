# Lab 2: Model Selection and Routing

Builds on Lab 1 (see `plans/lab-spec.md`). Theory: Section 2, choosing models and services.

## 1. Spec

**Goal.** Stop guessing which model to use. Deploy a second, larger model, measure both on the same labelled expenses, then route each task to the cheapest model that meets its quality bar.

**Requirements**
1. Two deployments in the same Foundry resource: `gpt-4.1-mini` (exists) and `gpt-4o` (new).
2. A labelled evaluation set (description -> correct category) that includes ambiguous cases.
3. A comparison script reporting accuracy, latency, tokens and estimated cost per model.
4. A small router (`app/ai/model_router.py`) that maps a task name to a deployment. Callers never hardcode a deployment.
5. `app/` core stays independent of Azure (principle 5).

**Constraints.** Keyless auth, capacity 10 per deployment, `max_output_tokens` on every call, everything inside `rg-expense-ai`.

### Decision table

| # | Decision | Why | Rejected alternative | Change when |
|---|---|---|---|---|
| D15 | Compare against `gpt-4o` (bigger, non-reasoning) | `gpt-4.1` was the first choice but this subscription has 0 quota for it (`InsufficientQuota`). `gpt-4o` is a larger non-reasoning model with quota, so size stays the main variable | `gpt-4.1` (no quota); reasoning models `o4-mini`/`gpt-5-mini`: slower and bill hidden reasoning tokens, which muddies a first comparison | Quota for `gpt-4.1` is granted, or Lab 4 needs multi-step reasoning |
| D16 | Measure on a labelled set, not by feel | Model choice is an engineering decision; accuracy, latency and cost are numbers | "The big one is smarter" | The set grows or data drifts (re-run the comparison) |
| D17 | Include ambiguous items in the set | Easy items make every model look perfect; ambiguity is where size matters | Only clear-cut items | Real misclassifications show up in production, add them |
| D18 | Route by task in code (`categorize` -> mini, `advise` -> gpt-4o) | Cost follows volume: categorization runs on every expense, advice rarely | One model for everything | Measured accuracy of mini is below the bar, or traffic mix changes |
| D19 | Router config comes from env vars | Swapping a model is a config change, not a code change, and works in CI/CD | Deployment names in code | Never, this is the standard pattern |
| D20 | Second deployment is `Standard` (not GlobalStandard), capacity 10 | Quota is per model AND per deployment type: `Standard.gpt-4o` had 50, GlobalStandard had none. Still pay per token, idle costs nothing, and processing stays regional (a bonus for data residency) | GlobalStandard: no quota here | Same triggers as D5 |

## 2. Prerequisites and cost

- Lab 1 working: `source .venv/bin/activate`, `az login` active, `python -m app.ai.lab01_smoke_test` passes.
- **What bills:** tokens only. The eval set is 12 short items run on 2 models, so the whole lab costs a few cents. An idle deployment bills nothing (D5).
- **Guardrails:** capacity 10 caps spend speed (429 instead of a big bill); everything is in `rg-expense-ai`.
- **Cleanup (optional, at the end of all labs):** `az group delete -n rg-expense-ai`. Deleting just the new deployment: `az cognitiveservices account deployment delete` with the same `-n`, `-g`, `--deployment-name`.
- Prices in the script come from the Azure Retail Prices API (`https://prices.azure.com/api/retail/prices`, no login) for swedencentral, and change over time. Note regional (Standard) costs about 21% more than global, and the Foundry compare page's "Estimated cost" is a benchmark index, not dollars.

## 3. Tasks

### Task 1: Deploy the larger model

**Objective.** A second deployment, `gpt-4o`, next to `gpt-4.1-mini`.

**Why CLI.** Repeatable, and it is the form Lab 5 (CI/CD) will reuse.

```bash
az cognitiveservices account deployment create \
  --name expense-advisor-resource \
  --resource-group rg-expense-ai \
  --deployment-name gpt-4o \
  --model-name gpt-4o \
  --model-version 2024-11-20 \
  --model-format OpenAI \
  --sku-name Standard \
  --sku-capacity 10
```

- `--name` is the Foundry **resource** (Lab 1 lesson), not the project.
- `--deployment-name` is what code passes as `model=` (Lab 1 self-check miss).
- **Quota is per model and per deployment type.** Our first attempt (`gpt-4.1`, GlobalStandard) failed with `InsufficientQuota`: limit 0 on this subscription. Find what you have with `az cognitiveservices usage list -l swedencentral -o json` and read the `name.value` and `limit` fields (the table view hides the names).

**Verify (UI).** Foundry portal -> your project -> Models + endpoints. Both deployments listed, state Succeeded.

**Common errors:** `InsufficientQuota` (limit 0 for that model/type: pick another model or type, or request quota; lowering capacity does not help when the limit is 0); `ResourceNotFound` (you passed the project name as `--name`).

### Task 2: Configuration

Append to `.env` and `.env.example` (make sure the file ends with a newline first, Lab 1 lesson):

```
FOUNDRY_ADVISOR_DEPLOYMENT=gpt-4o
```

### Task 3: Labelled evaluation set

**Objective.** Ground truth to measure against.

**Why.** Rows 1-8 are clear; rows 9-12 are ambiguous on purpose (D17). Categories must match `app/models/category.py` exactly.

Create `app/ai/labs/lab02_eval_set.json`:

```json
[
  {"description": "Starbucks latte", "label": "Food"},
  {"description": "Uber ride to airport", "label": "Transport"},
  {"description": "Netflix monthly subscription", "label": "Entertainment"},
  {"description": "Electricity bill October", "label": "Utilities"},
  {"description": "Lidl groceries", "label": "Food"},
  {"description": "Monthly metro pass", "label": "Transport"},
  {"description": "Cinema tickets", "label": "Entertainment"},
  {"description": "Internet and phone plan", "label": "Utilities"},
  {"description": "Dinner and a movie night", "label": "Entertainment"},
  {"description": "Gas station: fuel and a sandwich", "label": "Transport"},
  {"description": "Spotify family plan", "label": "Entertainment"},
  {"description": "Gift for a colleague", "label": "Other"}
]
```

Rows 9-12 are judgment calls. If you disagree with a label, change it and note why: the point is a *consistent* standard, and the disagreement is itself the lesson about ambiguity.

### Task 4: Comparison script

**Objective.** Same prompt, same data, two models; compare accuracy, latency, tokens, cost.

**Why this design.** Identical instructions isolate the model as the only variable. `perf_counter` measures end-to-end latency as the app sees it. Token counts come from `response.usage`, so cost is computed from real usage, not guessed.

Create `app/ai/labs/lab02_compare.py`:

```python
import json
import os
import time
from pathlib import Path

from app.ai.foundry_client import get_openai_client
from app.models import Category

CATEGORIES = [c.value for c in Category]

INSTRUCTIONS = (
    "You categorize personal expenses. "
    f"Answer with exactly one of: {', '.join(CATEGORIES)}. No other text."
)

# USD per 1M tokens: (input, output). From the Azure Retail Prices API, swedencentral.
PRICES = {
    os.environ["FOUNDRY_MODEL_DEPLOYMENT"]: (0.40, 1.60),    # gpt-4.1-mini
    os.environ["FOUNDRY_ADVISOR_DEPLOYMENT"]: (3.025, 12.10),  # gpt-4o, Standard (regional)
}

client = get_openai_client()
items = json.loads((Path(__file__).parent / "lab02_eval_set.json").read_text())


def evaluate(deployment: str) -> dict:
    correct = in_tok = out_tok = 0
    latencies = []
    for item in items:
        start = time.perf_counter()
        response = client.responses.create(
            model=deployment,
            instructions=INSTRUCTIONS,
            input=item["description"],
            max_output_tokens=16,
        )
        latencies.append(time.perf_counter() - start)
        in_tok += response.usage.input_tokens
        out_tok += response.usage.output_tokens
        answer = response.output_text.strip()
        ok = answer == item["label"]
        correct += ok
        if not ok:
            print(f"  [{deployment}] '{item['description']}' -> {answer} (expected {item['label']})")
    price_in, price_out = PRICES[deployment]
    return {
        "deployment": deployment,
        "accuracy": f"{correct}/{len(items)}",
        "avg_latency_s": round(sum(latencies) / len(latencies), 2),
        "tokens": in_tok + out_tok,
        "cost_usd": round((in_tok * price_in + out_tok * price_out) / 1_000_000, 6),
    }


for dep in PRICES:
    print(evaluate(dep))
```

Run: `python -m app.ai.labs.lab02_compare`

**Expected output.** One dict per model plus a line for each wrong answer. Typical shape: both near-perfect on rows 1-8; differences (if any) on rows 9-12; `gpt-4o` roughly 7x the cost per token. Your numbers will differ.

**Read the result with these questions:**
1. Did the big model win on accuracy? By how much, and on which rows?
2. If the gap is zero or one ambiguous row, is the cost multiple worth it for *every* expense?
3. Are the "wrong" answers actually wrong, or is the label debatable?

**Common errors:** `KeyError: FOUNDRY_ADVISOR_DEPLOYMENT` (Task 2 not done or `.env` not reloaded); `429` (capacity 10 is small; wait a minute or add a short `time.sleep(1)` between calls); accuracy 0 on everything (the model added punctuation, so `strip()` is not enough; check `max_output_tokens` and the printed answers).

### Task 5: The router

**Objective.** One function every feature calls, so no caller knows a deployment name.

**Why.** D18 and D19. The route is a policy; policy belongs in one place and in config.

Create `app/ai/model_router.py`:

```python
"""Maps a task to the cheapest deployment that meets its quality bar."""
import os

from app.ai.foundry_client import get_openai_client

# Task -> env var holding the deployment name. Config, not code (D19).
_ROUTES = {
    "categorize": "FOUNDRY_MODEL_DEPLOYMENT",    # high volume, simple: small model
    "advise": "FOUNDRY_ADVISOR_DEPLOYMENT",      # low volume, reasoning: large model
}


def deployment_for(task: str) -> str:
    try:
        return os.environ[_ROUTES[task]]
    except KeyError:
        raise ValueError(f"Unknown task or missing config: {task!r}") from None


def ask(task: str, instructions: str, user_input: str, max_output_tokens: int) -> str:
    response = get_openai_client().responses.create(
        model=deployment_for(task),
        instructions=instructions,
        input=user_input,
        max_output_tokens=max_output_tokens,
    )
    return response.output_text
```

Note it lives in `app/ai/` and is not imported by `app/__init__` or `app/ai/__init__` (D11 rule), so the core still runs without Azure.

Smoke test, `app/ai/labs/lab02_router_test.py`:

```python
from app.ai.model_router import ask, deployment_for

print(deployment_for("categorize"), deployment_for("advise"))
print(ask("categorize", "Answer with one word: the expense category.", "Lidl groceries", 16))
print(ask("advise", "You are a concise financial advisor.",
          "I spend 40% of income on food. Is that high? Two sentences.", 120))
```

Run: `python -m app.ai.labs.lab02_router_test`. Expect `gpt-4.1-mini gpt-4o`, a one-word category, and a short advisory answer.

## 4. Verification (UI)

Foundry portal -> Monitor (or the resource's Metrics in Azure portal): request count and token usage should show both deployments with traffic from your runs. This confirms routing really hit different models, which the printed names alone do not prove.

## 5. Self-check (exam style)

Each question is multiple choice. A question says "Choose two." when two answers are correct; otherwise exactly one is correct. Send your letters only and I will mark them.

1. Your app categorizes 50,000 expenses a day and answers about 20 advisory questions a day. Which routing minimizes cost without losing quality on the hard task?
   A. `gpt-4o` for both  B. `gpt-4.1-mini` for both  C. mini for categorization, `gpt-4o` for advice  D. `gpt-4o` for categorization, mini for advice
2. In `responses.create(model=...)`, what must the value be?
   A. The base model name  B. The deployment name  C. The resource name  D. The project name
3. A teammate wants to swap the advisor to a newer model next month. With the router from this lab, what changes?
   A. Every call site  B. The `.env` value and the deployment  C. `foundry_client.py` only  D. The Category enum
4. Why does the eval set include ambiguous rows?
   A. The Responses API rejects evaluation sets without them  B. They make the evaluation run faster  C. Clear rows make every model look perfect, so only the ambiguous rows show which model is better  D. They lower the cost of each evaluation request
5. What does a `429` at capacity 10 tell you?
   A. The deployment was deleted  B. The daily budget of 10 dollars is spent  C. The 10K tokens-per-minute cap was exceeded  D. Ten users are connected at once
6. A `429` appears at capacity 10. Which actions address it? Choose two.
   A. Disable the content filter  B. Retry with backoff  C. Raise capacity, if quota allows  D. Lower the temperature

Send your letters and I will mark them.

## 6. Decision recap

Model choice is data-driven (D16); the routing policy lives in one module (D18) and is configured by env vars (D19); the larger model is used only where it earns its price; the core app never imports Azure.

## 7. After the lab

Tell me your comparison results. I will then add D15-D20 and the lessons to `plans/lab-spec.md` and mark Lab 2 done.
