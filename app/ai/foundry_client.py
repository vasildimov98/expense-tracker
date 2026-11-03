"""Single place that knows how to talk to Microsoft Foundry."""
import os
from dotenv import load_dotenv
import openai
from azure.identity import DefaultAzureCredential, get_bearer_token_provider
from azure.ai.projects import AIProjectClient

load_dotenv()  # reads .env into environment variables


def get_project_client() -> AIProjectClient:
    # DefaultAzureCredential tries several sign-in sources in order. On your
    # laptop it finds your `az login` session, and in Azure it uses a managed
    # identity. So the same code works in both places, with no API key to leak.
    return AIProjectClient(
        credential=DefaultAzureCredential(),
        endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
    )


def get_openai_client():
    # The project client hands back a standard OpenAI client that is
    # already pointed at your Foundry resource.
    return get_project_client().get_openai_client()


def get_embeddings_client() -> openai.OpenAI:
    # The project-scoped endpoint does not serve /embeddings (empty 404), so
    # use the resource-level OpenAI v1 endpoint, still keyless: the token
    # provider fetches Entra tokens for the Foundry/Cognitive Services scope.
    resource = os.environ["FOUNDRY_PROJECT_ENDPOINT"].split("/api/projects")[0]
    token_provider = get_bearer_token_provider(
        DefaultAzureCredential(), "https://cognitiveservices.azure.com/.default"
    )
    return openai.OpenAI(base_url=f"{resource}/openai/v1/", api_key=token_provider)


DEPLOYMENT =os.environ["FOUNDRY_MODEL_DEPLOYMENT"]