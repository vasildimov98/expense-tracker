"""Publish the advisor with a named instructions variant, or restore the default (Lab 7 run B).

Run: python -m app.ai.labs.lab07_set_variant drop_grounding    # weakened, for run B
     python -m app.ai.labs.lab07_set_variant default           # ALWAYS restore afterwards
chat() uses the agent by name, so whichever version was published last is what runs.
"""
import sys

from app.ai.advisor_agent import create_agent, instructions_for

choice = sys.argv[1] if len(sys.argv) > 1 else "default"
variant = None if choice == "default" else choice
print("Instructions being published:\n", instructions_for(variant), "\n")
print(f"Published expense-advisor version {create_agent(variant).version} ({choice})")
