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

@description('Lab 6: Log Analytics workspace + Application Insights + the project connection Foundry Tracing reads (D62).')
param deployMonitoring bool = false
param workspaceName string = 'log-expense-advisor'
param appInsightsName string = 'appi-expense-advisor'

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
  dependsOn: [
    project
  ]
  name: d.name                       // the deployment NAME your code passes as model=
  sku: { name: d.sku, capacity: d.capacity }
   properties: {
    model: { format: 'OpenAI', name: d.model, version: d.version }
    versionUpgradeOption: 'NoAutoUpgrade'   // D7 made real: no silent model changes
    raiPolicyName: 'Microsoft.DefaultV2'    // the content filter policy, now explicit (Lab 7 changes it)
  }
}]

resource search 'Microsoft.Search/searchServices@2025-05-01' = if (deploySearch) {
  name: searchName
  location: searchLocation
  sku: { name: 'free' }
  properties: {
    replicaCount: 1
    partitionCount: 1
    // D65: keyless is enforced. Search rejects authOptions together with disableLocalAuth,
    // so authOptions is deliberately absent. Entra ID is then the only way in.
    disableLocalAuth: true
  }
}

// ---- Lab 6 monitoring (D62): these three were created by hand during the lab ----
resource workspace 'Microsoft.OperationalInsights/workspaces@2023-09-01' = if (deployMonitoring) {
  name: workspaceName
  location: location
  properties: {
    sku: { name: 'PerGB2018' }
    retentionInDays: 30
  }
}

resource appInsights 'Microsoft.Insights/components@2020-02-02' = if (deployMonitoring) {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: workspace.id    // workspace-based, so KQL and retention live in Log Analytics
  }
}

// The connection the Foundry Tracing tab and telemetry.setup() read the connection string from.
resource appInsightsConnection 'Microsoft.CognitiveServices/accounts/projects/connections@2025-06-01' = if (deployMonitoring) {
  parent: project
  name: 'appinsights'
  properties: {
    category: 'AppInsights'
    target: appInsights.id
    authType: 'ApiKey'
    isSharedToAll: false    // what-if showed the service keeps false even though the hand-made PUT sent true; match reality
    credentials: { key: appInsights!.properties.ConnectionString }   // same condition as this resource
    metadata: { ApiType: 'Azure', ResourceId: appInsights.id }
  }
}

output projectEndpoint string = 'https://${accountName}.services.ai.azure.com/api/projects/${projectName}'
output searchEndpoint string = deploySearch ? 'https://${searchName}.search.windows.net' : ''
