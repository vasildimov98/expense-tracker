# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A study project with two halves: a layered Python CLI expense tracker (`app/models`, `app/storage`, `app/services`, `app/cli`) used to learn Python from C#, and an "Expense Advisor" built on Microsoft Foundry and Azure AI Search (`app/ai/`, `infra/`) used to prepare for the AI-103 exam. The user is learning. Since 2026-11-18 (Lab 8) Claude WRITES the code in learning sessions; the user cares about shapes, purposes and the alternative approaches and tools, not syntax (see "Learning sessions" and memory). `study/` holds exam notes, `plans/` holds step and lab plans.

## Commands

```bash
source .venv/bin/activate
python main.py                          # run the CLI tracker (needs no Azure)
pip install -r requirements-dev.txt     # dev deps (includes requirements-ai.txt, pinned)
python -m pytest -q                     # all tests; CI runs exactly this on Python 3.14
python -m pytest tests/test_usage.py::test_name   # single test
az bicep build --file infra/main.bicep --stdout > /dev/null   # CI's Bicep compile check
```

There is no linter configured. Lab scripts run as modules from the repo root, e.g. `python -m app.ai.labs.lab03_query "question"`.

## Hard rules

- **Never run `az` or any code that calls Azure.** Write the scripts and commands, the user runs them. Tests must never reach Azure: `tests/conftest.py` injects dummy `FOUNDRY_*`/`AZURE_SEARCH_*` env vars so Azure-reading modules import offline.
- **`app/` core must run and test without Azure configured.** Only `app/ai/` may import Azure/OpenAI SDKs.
- **Keyless auth only** (`DefaultAzureCredential`); no secrets in code or git. `.env` is git-ignored, copy from `.env.example`.
- Update `scripts/azure/rebuild.sh` after every lab that changes the Azure environment (the account moves from a personal trial to a work account around Dec 2026).

## Architecture

**CLI core** (dependency direction `main.py -> cli -> services -> models`, `main.py -> storage -> models`): services hold the rules with no I/O or printing; `cli` owns all input/printing; `main.py` only wires objects together. Data lives in `expenses.json` (git-ignored); a corrupt file is moved to `expenses.bak` and the app starts empty.

**AI layer (`app/ai/`)**: `foundry_client.py` is the single place that builds clients (project client, OpenAI client, a separate embeddings client because the project-scoped endpoint does not serve `/embeddings`). Everything else goes through it:
- `model_router.py` maps a task (categorize, advise) to a deployment, with optional comma-separated fallbacks from `FOUNDRY_FALLBACK_*`; `resilience.py` does retry-with-backoff on 429 then fails over to the fallback deployment.
- `retrieval.py` / `search_client.py` do vector search over Azure AI Search (index built by `labs/lab03_build_index.py`).
- `advisor_agent.py` defines the Foundry agent; its tools (`advisor_tools.py`) are executed locally in a bounded loop (`MAX_TOOL_ROUNDS`). The agent cannot write: its only write-shaped tool, `propose_expense`, creates a pending proposal (`proposals.py`) that a human approves in `labs/lab08_review.py` (Lab 8).
- `usage.py` / `telemetry.py` write token usage to `usage.jsonl` (git-ignored) and OpenTelemetry to Application Insights.
- `labs/` are runnable lab scripts, not library code; `lab02_eval_set.json` and `lab03_seed_expenses.json` are their fixtures.

**Infra**: `infra/main.bicep` provisions the Foundry account, project, model deployments, and (behind `deploySearch` / `deployMonitoring` flags) Search, Log Analytics and App Insights. Per-environment params are `dev|test|work.bicepparam`; `network-test.bicep` is the private-networking experiment. `rebuild.sh` handles only what is not IaC (provider registration, resource group, role assignments, printing `.env` values) and needs `ACCOUNT` and `SEARCH_NAME` exported. Role assignments are human-run on purpose. `.github/workflows/deploy-test.yml` is manual-only (`workflow_dispatch`) because the test resource group is deleted between labs.

## Where decisions live

`plans/lab-spec.md` is the living decision log (D1-D67, each with why and trade-off); read it before changing infra or AI-layer design, and add a decision there when making a new one. Per-lab plans are `plans/lab-0N-*.md`; the overall study plan and progress are in `plans/ai-103-study-plan.md`.

## Learning sessions

Every time the user starts a learning session (a lab, a study module, a tracker step), run it as an interactive workshop, like a Udemy instructor guiding a complete beginner, following the relevant plan file:

1. **Theory recap**: a brief, clear overview of the core concepts the session practises.
2. **Step-by-step walkthrough, one task at a time**: Task 1 only first. Explain what we do and why, highlight key concepts, shapes and patterns to remember, and pause after each step so the user can confirm before moving on.
3. **Wrap-up quiz**: after all tasks, a short interactive exam-style quiz.

**Code in learning sessions (updated 2026-11-18):** Claude writes the code. With each piece, flag (a) the *shape* worth remembering (the pattern and its purpose), (b) the *alternative approaches and tools* for the same job and when each fits, and (c) only the syntax that differs from C#. Syntax details are not the point.
