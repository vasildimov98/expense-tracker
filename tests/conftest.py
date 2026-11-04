import os

# Dummy values so Azure-reading modules import. No test talks to Azure.
for key, value in {
    "FOUNDRY_PROJECT_ENDPOINT": "https://example.services.ai.azure.com/api/projects/test",
    "FOUNDRY_MODEL_DEPLOYMENT": "mini",
    "FOUNDRY_ADVISOR_DEPLOYMENT": "advisor",
    "FOUNDRY_EMBEDDING_DEPLOYMENT": "embed",
    "AZURE_SEARCH_ENDPOINT": "https://example.search.windows.net",
    "AZURE_SEARCH_INDEX": "expenses",
}.items():
    os.environ.setdefault(key, value)