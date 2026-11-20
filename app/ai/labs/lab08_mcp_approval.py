"""Lab 8, Task 4: approve a hosted MCP tool call through the Responses API (D88).

    python -m app.ai.labs.lab08_mcp_approval ["a generic documentation question"]

Prerequisite: the portal agent has the learn-docs MCP tool with approval = "Never auto-approve tools".
This script does NOT call create_agent(): that would publish a version without the MCP tool.
Field names of the approval items are printed, not assumed: read them and adapt if they differ.
Do NOT ask about your expenses: a question sent to a non-Foundry tool leaves the Azure boundary.
"""
import getpass
import sys

from app.ai import audit
from app.ai.advisor_agent import AGENT_NAME, _client

QUESTION = sys.argv[1] if len(sys.argv) > 1 else "How do I create an Azure Storage account? Use the docs tool."
AGENT = {"extra_body": {"agent_reference": {"name": AGENT_NAME, "type": "agent_reference"}},
         "max_output_tokens": 800}
APPROVER = getpass.getuser()

response = _client().responses.create(input=QUESTION, **AGENT)
print("output item types:", [item.type for item in response.output])

requests = [item for item in response.output if item.type == "mcp_approval_request"]
if not requests:
    print("No approval request: either the tool was not used or approval is set to auto. Answer:")
    print(response.output_text)
    sys.exit(0)

decisions = []
for req in requests:
    print("\n--- approval request (raw) ---")
    print(req.model_dump_json(indent=2) if hasattr(req, "model_dump_json") else req)
    approve = input(f"\nApprove {req.name} on {req.server_label}? [y/N] ").strip().lower() == "y"
    # D81: the arguments echo the user's words, so the audit keeps a hash, not the text.
    audit.write("mcp_approval", APPROVER, tool=req.name, server=req.server_label,
                args_hash=audit.digest(str(req.arguments)), approved=approve, request_id=req.id)
    decisions.append({"type": "mcp_approval_response", "approval_request_id": req.id, "approve": approve})

final = _client().responses.create(input=decisions, previous_response_id=response.id, **AGENT)
print("\noutput item types after approval:", [item.type for item in final.output])
print("\nAnswer:", final.output_text or "(none: the call was denied or nothing was returned)")
