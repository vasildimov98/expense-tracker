targetScope = 'resourceGroup'

@description('Globally unique account name for the network test')
param accountName string 
@description('Public network access for the account (Enabled or Disabled)')
param publicAccess 'Enabled' | 'Disabled' = 'Enabled'
param location string = resourceGroup().location

@description('DNS zone for the network test')
var dnsZones array = ['privatelink.cognitiveservices.azure.com', 'privatelink.openai.azure.com', 'privatelink.services.ai.azure.com']

resource account 'Microsoft.CognitiveServices/accounts@2025-06-01' = {
  name: accountName
  location: location
  kind: 'AIServices'
  sku: { name: 'S0' }
  identity: { type: 'SystemAssigned' }
  properties: {
    customSubDomainName: accountName
    publicNetworkAccess: publicAccess
    disableLocalAuth: true          // D45: keyless is enforced, not just practiced
  }
}

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2024-05-01' = {
  name: '${accountName}-vnet'
  location: location
  properties: {
    addressSpace: {
      addressPrefixes: [
        '10.0.0.0/16'
      ]
    }
    subnets: [
      {
        name: 'default'
        properties: {
          addressPrefix: '10.0.0.0/24'
        }
      }
    ]
  }
}


resource privateEndpoint 'Microsoft.Network/privateEndpoints@2024-05-01' = {
  name: '${accountName}-pe'
  location: location
  properties: {
    subnet: {
      id: virtualNetwork.properties.subnets[0].id
      
    }
    privateLinkServiceConnections: [
      {
        name: '${accountName}-pls'
        properties: {
          privateLinkServiceId: account.id
          groupIds: [
            'account'
          ]
        }
      }
    ]
  }
}

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = [for zone in dnsZones: {
  name: zone
  location: 'global'
}]

resource virtualNetworkLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = [for (zone, i) in dnsZones: {
  parent: privateDnsZone[i]
  name: '${accountName}-vnet-link'
  location: 'global'
  properties: {
    virtualNetwork: {
      id: virtualNetwork.id
    }
    registrationEnabled: false
  }
}]

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2024-05-01' = {
  parent: privateEndpoint
  name: 'dnszonegroup'
  properties: {
    privateDnsZoneConfigs: [for (zone, i) in dnsZones: {
      name: replace(zone, '.', '-')
      properties: {
        privateDnsZoneId: privateDnsZone[i].id
      }
    }]
  }
}
