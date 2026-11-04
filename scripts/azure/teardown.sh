#!/usr/bin/env bash
# Delete the whole Expense Advisor environment (D2: one group = one command).
# Usage: bash scripts/azure/teardown.sh        (asks before deleting)
set -euo pipefail

RG="${RG:-rg-expense-ai}"
ACCOUNT="${ACCOUNT:-expense-advisor-resource}"
LOCATION="${LOCATION:-swedencentral}"

echo "This deletes resource group '$RG' in subscription:"
az account show --query "{name:name, id:id}" -o tsv
read -r -p "Type the group name to confirm: " ans
[ "$ans" = "$RG" ] || { echo "Aborted."; exit 1; }

az group delete -n "$RG" --yes
# The AI account is soft-deleted and keeps its name and quota until purged.
az cognitiveservices account purge -n "$ACCOUNT" -g "$RG" -l "$LOCATION" \
  || echo "Purge failed or not needed: check 'az cognitiveservices account list-deleted -o table'"
