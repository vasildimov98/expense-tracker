import os
import time

from azure.ai.projects.models import (
    MemorySearchPreviewTool,
    MemoryStoreDefaultDefinition,
    MemoryStoreDefaultOptions,
    PromptAgentDefinition,
)

from app.ai.foundry_client import get_project_client
from app.ai.model_router import deployment_for

STORE = "expense-advisor-memory"
SCOPE = "user-vd91"                                  # D41: one scope per user
project = get_project_client()
client = project.get_openai_client()

try:
    project.beta.memory_stores.delete(STORE)         # start clean on re-runs
except Exception:
    pass

project.beta.memory_stores.create(
    name=STORE,
    definition=MemoryStoreDefaultDefinition(
        chat_model=os.environ["FOUNDRY_MODEL_DEPLOYMENT"],        # extracts the facts
        embedding_model=os.environ["FOUNDRY_EMBEDDING_DEPLOYMENT"],  # finds them later
        options=MemoryStoreDefaultOptions(
            user_profile_enabled=True, chat_summary_enabled=False
        ),
    ),
    description="Long-term memory for the expense advisor",
)

project.agents.create_version(
    agent_name="expense-advisor-mem",
    definition=PromptAgentDefinition(
        model=deployment_for("advise"),
        instructions="You are a concise financial advisor. Use what you remember about the user.",
        tools=[MemorySearchPreviewTool(
            memory_store_name=STORE, scope=SCOPE,
            update_delay=1,        # demo only: default is 300 s of inactivity
        )],
    ),
)
agent = {"extra_body": {"agent_reference": {"name": "expense-advisor-mem", "type": "agent_reference"}},
         "max_output_tokens": 150}

first = client.responses.create(
    input="Remember: my monthly food budget is 200 euros and I prefer short answers.", **agent)
print("Conversation 1:", first.output_text)

time.sleep(25)     # memories are extracted asynchronously

second = client.responses.create(input="What is my food budget?", **agent)  # NEW conversation
print("Conversation 2:", second.output_text)