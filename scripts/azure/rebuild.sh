#!/usr/bin/env bash
# Rebuild the Expense Advisor Azure environment (Labs 1-4) in the CURRENTLY LOGGED-IN subscription.
# Decisions behind every value: plans/lab-spec.md (D1-D42).
#
# Usage:
#   az login                                  # the NEW account
#   az account set --subscription <id-or-name>
#   export SEARCH_NAME=srch-expense-advisor-<unique>   # must be globally unique
#   bash scripts/azure/rebuild.sh
#
# Safe to re-run: every step checks whether the thing exists first.
# NOT verified by the author (no Azure access when written): the two `az rest` calls
# (account + project). If one fails, create that item in the portal with the same
# names and re-run; the script skips what exists.
set -euo pipefail

# ---- configuration (override with env vars) ---------------------------------
RG="${RG:-rg-expense-ai}"                              # D2
LOCATION="${LOCATION:-swedencentral}"                  # D3
ACCOUNT="${ACCOUNT:-expense-advisor-resource}"         # Foundry resource name; must be globally unique
PROJECT="${PROJECT:-expense-advisor}"                  # D1
SEARCH_NAME="${SEARCH_NAME:?set SEARCH_NAME to a globally unique, lowercase name}"
SEARCH_LOCATION="${SEARCH_LOCATION:-northeurope}"      # D31 (swedencentral ran out of capacity)
API_VERSION="2025-06-01"                               # Microsoft.CognitiveServices ARM API

# name | model | version | sku | capacity     (D4-D7, D15, D20, D23)
DEPLOYMENTS=(
  "gpt-4.1-mini|gpt-4.1-mini|2025-04-14|GlobalStandard|10"
  "gpt-4o|gpt-4o|2024-11-20|Standard|10"
  "text-embedding-3-small|text-embedding-3-small|1|GlobalStandard|10"
)

say() { printf '\n== %s\n' "$*"; }
SUB=$(az account show --query id -o tsv)
ME=$(az ad signed-in-user show --query id -o tsv)
say "Subscription $SUB, user $ME"

# ---- 1. providers + resource group ------------------------------------------
say "Register providers (one-time per subscription)"
for ns in Microsoft.CognitiveServices Microsoft.Search; do
  az provider register --namespace "$ns" --wait
done

say "Resource group $RG"
az group create -n "$RG" -l "$LOCATION" -o none

# ---- 2. Foundry resource (kind AIServices) + project ------------------------
ACCOUNT_ID="/subscriptions/$SUB/resourceGroups/$RG/providers/Microsoft.CognitiveServices/accounts/$ACCOUNT"

if az cognitiveservices account show -n "$ACCOUNT" -g "$RG" -o none 2>/dev/null; then
  say "Foundry resource $ACCOUNT exists, skipping"
else
  say "Create Foundry resource $ACCOUNT"
  # allowProjectManagement is what makes it a Foundry resource that can hold projects.
  az rest --method put --url "https://management.azure.com$ACCOUNT_ID?api-version=$API_VERSION" \
    --body "{
      \"location\": \"$LOCATION\",
      \"kind\": \"AIServices\",
      \"sku\": {\"name\": \"S0\"},
      \"identity\": {\"type\": \"SystemAssigned\"},
      \"properties\": {
        \"customSubDomainName\": \"$ACCOUNT\",
        \"allowProjectManagement\": true,
        \"publicNetworkAccess\": \"Enabled\"
      }
    }" -o none
  until [ "$(az cognitiveservices account show -n "$ACCOUNT" -g "$RG" --query properties.provisioningState -o tsv)" = "Succeeded" ]; do
    echo "  waiting for the account..."; sleep 10
  done
fi

if az rest --method get --url "https://management.azure.com$ACCOUNT_ID/projects/$PROJECT?api-version=$API_VERSION" -o none 2>/dev/null; then
  say "Project $PROJECT exists, skipping"
else
  say "Create project $PROJECT"
  az rest --method put --url "https://management.azure.com$ACCOUNT_ID/projects/$PROJECT?api-version=$API_VERSION" \
    --body "{
      \"location\": \"$LOCATION\",
      \"identity\": {\"type\": \"SystemAssigned\"},
      \"properties\": {\"displayName\": \"$PROJECT\", \"description\": \"Expense Advisor project\"}
    }" -o none
  sleep 20
fi

# ---- 3. model deployments (one at a time: concurrent operations are rejected) ---
for row in "${DEPLOYMENTS[@]}"; do
  IFS='|' read -r NAME MODEL VERSION SKU CAP <<< "$row"
  if az cognitiveservices account deployment show -n "$ACCOUNT" -g "$RG" --deployment-name "$NAME" -o none 2>/dev/null; then
    say "Deployment $NAME exists, skipping"; continue
  fi
  say "Deploy $NAME ($MODEL $VERSION, $SKU, capacity $CAP)"
  az cognitiveservices account deployment create -n "$ACCOUNT" -g "$RG" \
    --deployment-name "$NAME" --model-name "$MODEL" --model-version "$VERSION" \
    --model-format OpenAI --sku-name "$SKU" --sku-capacity "$CAP" -o none || {
      echo "!! $NAME failed. 'InsufficientQuota ... 0 / 0' means this model/type has no quota in $LOCATION."
      echo "   Find usable quota:  az cognitiveservices usage list -l $LOCATION -o json"
      echo "   Then re-run with that SKU edited in DEPLOYMENTS (lab-spec Lessons, Lab 2)."
      exit 1; }
done

# ---- 4. Azure AI Search (Free tier, one per subscription, D22) --------------
if az search service show -n "$SEARCH_NAME" -g "$RG" -o none 2>/dev/null; then
  say "Search service $SEARCH_NAME exists, skipping"
else
  say "Create Search service $SEARCH_NAME in $SEARCH_LOCATION"
  # A just-deleted service keeps its name for a few minutes (error ServiceDeleting): retry.
  for attempt in 1 2 3 4 5 6 7 8 9 10; do
    if out=$(az search service create -n "$SEARCH_NAME" -g "$RG" -l "$SEARCH_LOCATION" --sku free \
        --auth-options aadOrApiKey --aad-auth-failure-mode http401WithBearerChallenge -o none 2>&1); then
      break
    fi
    if [[ "$out" == *ServiceDeleting* && $attempt -lt 10 ]]; then
      echo "  name still being released (attempt $attempt/10), waiting 60 s..."; sleep 60
    else
      echo "$out" >&2; exit 1
    fi
  done
fi

# ---- 5. roles for YOUR user (data plane, D8, D28) ---------------------------
say "Role assignments (propagation takes 1-2 min; a 403 right after is normal)"
SEARCH_ID=$(az search service show -n "$SEARCH_NAME" -g "$RG" --query id -o tsv)
for role in "Search Service Contributor" "Search Index Data Contributor" "Search Index Data Reader"; do
  az role assignment create --assignee "$ME" --role "$role" --scope "$SEARCH_ID" -o none
done
# The role was renamed from "Azure AI User" to "Foundry User"; accept either name.
az role assignment create --assignee "$ME" --role "Foundry User" --scope "$ACCOUNT_ID" -o none 2>/dev/null \
  || az role assignment create --assignee "$ME" --role "Azure AI User" --scope "$ACCOUNT_ID" -o none

# ---- 6. print the .env values -----------------------------------------------
say "Done. Put this in .env (keyless: no secrets are needed)"
cat <<EOF
FOUNDRY_PROJECT_ENDPOINT=https://$ACCOUNT.services.ai.azure.com/api/projects/$PROJECT
FOUNDRY_MODEL_DEPLOYMENT=gpt-4.1-mini
FOUNDRY_ADVISOR_DEPLOYMENT=gpt-4o
FOUNDRY_EMBEDDING_DEPLOYMENT=text-embedding-3-small
AZURE_SEARCH_ENDPOINT=https://$SEARCH_NAME.search.windows.net
AZURE_SEARCH_INDEX=expenses
EXPENSES_PATH=app/ai/labs/lab03_seed_expenses.json
EOF
cat <<'EOF'

Next (Python, from the project root, venv active; wait ~2 min for roles first):
  python -m app.ai.labs.lab01_smoke_test          # model answers
  python -m app.ai.labs.lab03_build_index         # recreates the index + 21 documents
  python -m app.ai.labs.lab04_chat                # creates the advisor agent, then chats
  python -m app.ai.labs.lab04_memory              # memory store + memory agent
EOF
