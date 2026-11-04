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
