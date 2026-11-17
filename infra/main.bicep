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

// ---- Lab 7 guardrails (D68-D71): the content filter policy is code, not the implicit default ----
var harmCategories = [
  { name: 'Hate', threshold: 'Medium' }
  { name: 'Sexual', threshold: 'Medium' }
  { name: 'Violence', threshold: 'Medium' }
  { name: 'Selfharm', threshold: 'Low' }      // D69: tightened, no legitimate need in this domain
]
var sources = [ 'Prompt', 'Completion' ]

resource policy 'Microsoft.CognitiveServices/accounts/raiPolicies@2025-06-01' = {
  parent: account
  dependsOn: [
    project    // serialize account writes: the first deploy hit RequestConflict when policy and project ran in parallel
  ]
  name: 'expense-advisor-policy'
  properties: {
    basePolicyName: 'Microsoft.DefaultV2'
    mode: 'Blocking'
    contentFilters: concat(
      flatten(map(harmCategories, c => map(sources, s => {
        name: c.name
        severityThreshold: c.threshold
        blocking: true
        enabled: true
        source: s
      }))),
      [
        // D70: two different attack paths, two shields. Both run on the prompt side
        // (retrieved documents and tool results reach the model inside the prompt).
        { name: 'Jailbreak', blocking: true, enabled: true, source: 'Prompt' }
        { name: 'Indirect Attack', blocking: true, enabled: true, source: 'Prompt' }
        // basePolicyName did not carry the default's protected-material filters over, so state them (D68: nothing implicit).
        // Same actions as the default: text blocks, code annotates (the advisor never writes code).
        { name: 'Protected Material Text', blocking: true, enabled: true, source: 'Completion' }
        { name: 'Protected Material Code', blocking: false, enabled: true, source: 'Completion' }
      ]
    )
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
    // Chat models get the custom policy (D68); embeddings do not generate text, so they keep the default.
    // Referencing policy.name also makes Bicep create the policy first.
    raiPolicyName: startsWith(d.model, 'text-embedding') ? 'Microsoft.DefaultV2' : policy.name
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
