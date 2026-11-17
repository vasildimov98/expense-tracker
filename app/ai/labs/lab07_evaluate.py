"""Lab 7 Task 4 step 2: score a responses file with built-in evaluators (D75, D76).

Run: python -m app.ai.labs.lab07_evaluate <label>
Reads  lab07_responses_<label>.jsonl (from lab07_build_eval_set), writes lab07_eval_<label>.json.

Judge = FOUNDRY_MODEL_DEPLOYMENT (gpt-4.1-mini), deliberately NOT the advisor model (D75). Keyless: DefaultAzureCredential.
Optional env: JUDGE_ENDPOINT, JUDGE_API_VERSION (defaults below, unverified for this account),
              EVAL_LOG_TO_FOUNDRY=1 to also log the run to the project so the portal can compare runs.
Evaluator inputs are exact names: groundedness(query, context, response), relevance(query, response).
A missing column gives a missing-input error, not a bad score.
"""
import json
import os
import sys
from pathlib import Path

from azure.ai.evaluation import GroundednessEvaluator, RelevanceEvaluator, evaluate
from azure.identity import DefaultAzureCredential
from dotenv import load_dotenv

load_dotenv()
HERE = Path(__file__).parent
label = sys.argv[1] if len(sys.argv) > 1 else "A"
data_path = HERE / f"lab07_responses_{label}.jsonl"
out_path = HERE / f"lab07_eval_{label}.json"

project_endpoint = os.environ["FOUNDRY_PROJECT_ENDPOINT"]
account = project_endpoint.split("//")[1].split(".")[0]
credential = DefaultAzureCredential()
model_config = {
    "azure_endpoint": os.environ.get("JUDGE_ENDPOINT", f"https://{account}.openai.azure.com"),
    "azure_deployment": os.environ["FOUNDRY_MODEL_DEPLOYMENT"],        # the judge deployment NAME
    "api_version": os.environ.get("JUDGE_API_VERSION", "2025-04-01-preview"),
    # No "credential" key here: the library's own validator type-checks it as typing.Any, which
    # Python 3.14 refuses (isinstance(x, Any)). The credential goes in the evaluator constructors below.
}

evaluators = {
    "groundedness": GroundednessEvaluator(model_config, credential=credential),
    "relevance": RelevanceEvaluator(model_config, credential=credential),
}
column_mapping = {
    "groundedness": {"column_mapping": {
        "query": "${data.query}", "context": "${data.context}", "response": "${data.response}"}},
    "relevance": {"column_mapping": {
        "query": "${data.query}", "response": "${data.response}"}},
}

kwargs = {}
if os.environ.get("EVAL_LOG_TO_FOUNDRY") == "1":
    kwargs["azure_ai_project"] = project_endpoint     # accepted forms differ by version: read the error if it complains

result = evaluate(
    data=str(data_path),
    evaluators=evaluators,
    evaluator_config=column_mapping,
    evaluation_name=f"lab07-{label}",
    output_path=str(out_path),
    **kwargs,
)

def _missing(row, metric):
    value = row.get(f"outputs.{metric}.{metric}")
    return not isinstance(value, (int, float)) or value != value     # None or NaN


incomplete = [(r.get("inputs.query"), m) for r in result["rows"] for m in ("groundedness", "relevance") if _missing(r, m)]
if incomplete:
    # A NaN row is dropped from the average, so run A and run B would be averaged over different rows (D75).
    print(f"\n!! INCOMPLETE RUN: {len(incomplete)} missing score(s), most likely judge 429s. Do NOT compare this run.")
    for query, metric in incomplete:
        print(f"   missing {metric}: {query}")
    print("   Rerun this command (429s are random), or give the judge deployment more capacity.")

print("\n== aggregate metrics")
for key, value in result["metrics"].items():
    print(f"  {key}: {value}")

rows = result["rows"]
print("\n== per row (kind | groundedness | relevance)   first row keys:", sorted(rows[0].keys()) if rows else [])
for row in rows:
    g = row.get("outputs.groundedness.groundedness")
    r = row.get("outputs.relevance.relevance")
    print(f"  {str(row.get('inputs.kind')):12} | g={g} | r={r} | {str(row.get('inputs.query'))[:55]}")

print("\n== judge reasons for rows scoring below 4 (explanation tooling, task step 5)")
for row in rows:
    for metric in ("groundedness", "relevance"):
        score = row.get(f"outputs.{metric}.{metric}")
        if isinstance(score, (int, float)) and score < 4:
            print(f"  [{metric}={score}] {row.get('inputs.query')}\n     response: {str(row.get('inputs.response'))[:120]!r}")
            print(f"     reason:   {row.get(f'outputs.{metric}.{metric}_reason')}")
print(f"\nSaved full result to {out_path}")
