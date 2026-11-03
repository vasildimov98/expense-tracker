"""Single place that knows how to talk to Azure AI Search."""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.indexes import SearchIndexClient

load_dotenv()

ENDPOINT = os.environ["AZURE_SEARCH_ENDPOINT"]
INDEX_NAME = os.environ["AZURE_SEARCH_INDEX"]
EMBEDDING_DEPLOYMENT = os.environ["FOUNDRY_EMBEDDING_DEPLOYMENT"]


def get_index_client() -> SearchIndexClient:
    # Manages indexes (create/delete): needs Search Service Contributor.
    return SearchIndexClient(ENDPOINT, DefaultAzureCredential())


def get_search_client() -> SearchClient:
    # Reads/writes documents inside one index.
    return SearchClient(ENDPOINT, INDEX_NAME, DefaultAzureCredential())