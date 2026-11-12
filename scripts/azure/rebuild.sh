#!/usr/bin/env bash
# Rebuild the Expense Advisor Azure environment (Labs 1-6) in the CURRENTLY LOGGED-IN subscription.
# Decisions behind every value: plans/lab-spec.md (D1-D67).
#
# Infrastructure (Foundry resource, project, model deployments, Search, and with deployMonitoring=true
# the Log Analytics workspace, Application Insights and the project's appinsights connection) comes from
# the reviewed Bicep template infra/main.bicep (Lab 5, D43-D44; monitoring Lab 6, D62). This script only does what is NOT
# infrastructure-as-code: provider registration, the resource group, the role assignments
# (human-run on purpose, D48) and printing the .env values.
#
# Usage:
#   az login                                  # the NEW account
#   az account set --subscription <id-or-name>
#   export ACCOUNT=expense-advisor-<unique>        # Foundry resource, globally unique
#   export SEARCH_NAME=srch-expense-advisor-<unique>   # globally unique, lowercase
#   bash scripts/azure/rebuild.sh
#
# Optional overrides: RG, LOCATION, SEARCH_LOCATION, PROJECT, ENV (default "work" -> infra/work.bicepparam),
# YES=1 to skip the confirmation after the what-if.
#
# Safe to re-run: Bicep deployments are idempotent and role assignments are skipped when they exist.
# NOT verified by the author: infra/work.bicepparam (readEnvironmentVariable) has not been compiled
# or deployed yet. If it fails, run `az bicep build-params --file infra/work.bicepparam --stdout`
# to see the compile error before touching Azure.
set -euo pipefail

# ---- configuration (override with env vars) ---------------------------------
RG="${RG:-rg-expense-ai}"                              # D2
export LOCATION="${LOCATION:-swedencentral}"           # D3 (read by the .bicepparam)
export ACCOUNT="${ACCOUNT:?set ACCOUNT to a globally unique Foundry resource name}"
export SEARCH_NAME="${SEARCH_NAME:?set SEARCH_NAME to a globally unique, lowercase name}"
export SEARCH_LOCATION="${SEARCH_LOCATION:-northeurope}"   # D31 (swedencentral ran out of capacity)
PROJECT="${PROJECT:-expense-advisor}"                  # D1 (must match main.bicep's projectName)
ENV="${ENV:-work}"
PARAMS="infra/$ENV.bicepparam"

say() { printf '\n== %s\n' "$*"; }
cd "$(dirname "$0")/../.."                              # repo root, so infra/ paths work
[ -f "$PARAMS" ] || { echo "missing $PARAMS" >&2; exit 1; }
SUB=$(az account show --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
say "Subscription $SUB, user $ME, parameters $PARAMS"

# ---- 1. providers + resource group ------------------------------------------
say "Register providers (one-time per subscription)"
for ns in Microsoft.CognitiveServices Microsoft.Search; do
  az provider register --namespace "$ns" --wait
done

say "Resource group $RG"
az group create -n "$RG" -l "$LOCATION" -o none

# ---- 2. infrastructure from Bicep: preview, confirm, deploy -----------------
# Replaces the old az/az rest sections for the account, project, deployments and Search.
say "What-if (preview only; read '+' and '~' lines, '-' lines for properties we do not set are noise)"
az deployment group what-if -g "$RG" -p "$PARAMS"

if [ "${YES:-}" != "1" ]; then
  read -r -p "Deploy this to $RG? [y/N] " answer
  [[ "$answer" == [yY] ]] || { echo "Stopped before deploying."; exit 0; }
fi

say "Deploy (a just-deleted Search name can fail with ServiceDeleting: wait a few minutes and re-run)"
az deployment group create -g "$RG" -n rebuild -p "$PARAMS" -o none

PROJECT_ENDPOINT=$(az deployment group show -g "$RG" -n rebuild --query properties.outputs.projectEndpoint.value -o tsv)
SEARCH_ENDPOINT=$(az deployment group show -g "$RG" -n rebuild --query properties.outputs.searchEndpoint.value -o tsv)

# ---- 3. roles for YOUR user (data plane, D8, D28, D48) ----------------------
say "Role assignments (propagation takes 1-2 min; a 403 right after is normal)"
ACCOUNT_ID="/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$ACCOUNT"
SEARCH_ID=$(az search service show -n "$SEARCH_NAME" -g "$RG" --query id -o tsv)
# Index Data Reader is not needed for you: Index Data Contributor already includes it (Lab 6 role audit).
for role in "Search Service Contributor" "Search Index Data Contributor"; do
  az role assignment create --assignee "$ME" --role "$role" --scope "$SEARCH_ID" -o none
done
# The role was renamed from "Azure AI User" to "Foundry User"; accept either name.
az role assignment create --assignee "$ME" --role "Foundry User" --scope "$ACCOUNT_ID" -o none 2>/dev/null \
  || az role assignment create --assignee "$ME" --role "Azure AI User" --scope "$ACCOUNT_ID" -o none

# ---- 3b. runtime identity for the deployed app (Lab 6, D65-D66) -------------
# A user-assigned managed identity: no secret to store, can be attached to a host later.
# Least privilege: it can call models/agents in the project and READ the index, nothing else.
say "Runtime identity id-expense-advisor-app and its two roles"
az identity create -g "$RG" -n id-expense-advisor-app -l "$LOCATION" -o none
APP_PRINCIPAL=$(az identity show -g "$RG" -n id-expense-advisor-app --query principalId -o tsv)
PROJECT_ID="$ACCOUNT_ID/projects/$PROJECT"
az role assignment create --assignee-object-id "$APP_PRINCIPAL" --assignee-principal-type ServicePrincipal \
  --role "Foundry User" --scope "$PROJECT_ID" -o none 2>/dev/null \
  || az role assignment create --assignee-object-id "$APP_PRINCIPAL" --assignee-principal-type ServicePrincipal \
       --role "Azure AI User" --scope "$PROJECT_ID" -o none
az role assignment create --assignee-object-id "$APP_PRINCIPAL" --assignee-principal-type ServicePrincipal \
  --role "Search Index Data Reader" --scope "$SEARCH_ID" -o none

# ---- 4. print the .env values (endpoints come from the deployment outputs) --
say "Done. Put this in .env (keyless: no secrets are needed)"
cat <<EOF
FOUNDRY_PROJECT_ENDPOINT=$PROJECT_ENDPOINT
FOUNDRY_MODEL_DEPLOYMENT=gpt-4.1-mini
FOUNDRY_ADVISOR_DEPLOYMENT=gpt-4o
FOUNDRY_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_SEARCH_ENDPOINT=$SEARCH_ENDPOINT
AZURE_SEARCH_INDEX=expenses
EXPENSES_PATH=app/ai/labs/lab03_seed_expenses.json
EOF
cat <<'EOF'

Next (Python, from the project root, venv active; wait ~2 min for roles first):
  python -m app.ai.labs.lab01_smoke_test          # model answers
  python -m app.ai.labs.lab03_build_index         # recreates the index + 21 documents
  python -m app.ai.labs.lab04_chat                # creates the advisor agent, then chats
  python -m app.ai.labs.lab04_memory              # memory store + memory agent
  python -m app.ai.labs.lab06_index_health        # count parity + golden queries (expects PASS)
  python -m app.ai.labs.lab06_telemetry_run       # sends traces to Application Insights (wait 2-5 min)
EOF
