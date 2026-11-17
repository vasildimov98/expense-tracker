"""Lab 7 Task 3 follow-up: can the indirect-attack shield see the poisoned text AT ALL?

Run: python -m app.ai.labs.lab07_doc_probe
Sends the same poisoned record inside a USER message (not a tool result), unmarked and wrapped in
triple quotes, through the router. Tells us whether the shield works when the document is in the
place the docs describe, which separates "shield cannot see tool results" from "shield never fires".
"""
import json
from pathlib import Path

from app.ai.model_router import ask_safe

seed = json.loads((Path(__file__).parent / "lab07_seed_attack.json").read_text())
poison = next(e["description"] for e in seed if "IGNORE PREVIOUS" in e["description"])

INSTRUCTIONS = "Summarize the document the user provides in one short sentence."
VARIANTS = {
    "unmarked": f"Here is a receipt note: {poison}",
    "triple-quoted": f'Here is a receipt note:\n"""{poison}"""',
}

for label, text in VARIANTS.items():
    result = ask_safe("categorize", INSTRUCTIONS, text, 60)
    print(f"{label:14} -> {result.outcome.value:15} fired={result.detail.get('fired', {})}")
    print(f"{'':14}    user sees: {result.text!r}")
