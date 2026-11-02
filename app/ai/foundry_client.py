"""Single place that knows how to talk to Microsoft Foundry."""
import os
from dotenv import load_dotenv
from azure.identity import DefaultAzureCredential
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


DEPLOYMENT = os.environ["FOUNDRY_MODEL_DEPLOYMENT"]