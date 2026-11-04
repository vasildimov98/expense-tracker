using 'main.bicep'

param accountName = 'expense-advisor-test-vd91'
param location = 'swedencentral'
param deploySearch = false
param deployments = [
  { name: 'text-embedding-3-small', model: 'text-embedding-3-small', version: '1', sku: 'GlobalStandard', capacity: 1 }
]
