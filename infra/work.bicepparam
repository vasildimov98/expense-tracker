using 'main.bicep'

// Parameters for rebuilding the Expense Advisor in a NEW subscription (personal -> work account).
// Globally unique names come from environment variables set by scripts/azure/rebuild.sh,
// so no name is hard-coded here and nothing from the old subscription is reused.
// readEnvironmentVariable() without a default FAILS when the variable is missing (loud, on purpose).
//
// Before the first run in a new subscription, re-check quota per region and model (Lab 2 lesson):
//   az cognitiveservices usage list -l <region> -o json
// and edit `deployments` below if a model or deployment type has a limit of 0.

param accountName = readEnvironmentVariable('ACCOUNT')
param location = readEnvironmentVariable('LOCATION', 'swedencentral')
param deploySearch = true
param searchName = readEnvironmentVariable('SEARCH_NAME')
param searchLocation = readEnvironmentVariable('SEARCH_LOCATION', 'northeurope')
param deployments = [
  { name: 'gpt-4.1-mini', model: 'gpt-4.1-mini', version: '2025-04-14', sku: 'GlobalStandard', capacity: 10 }
  { name: 'gpt-4o', model: 'gpt-4o', version: '2024-11-20', sku: 'Standard', capacity: 10 }
  { name: 'text-embedding-3-small', model: 'text-embedding-3-small', version: '1', sku: 'GlobalStandard', capacity: 10 }
]
