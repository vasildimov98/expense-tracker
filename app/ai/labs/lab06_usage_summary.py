"""Summarize usage.jsonl: calls, tokens and cost per (task, deployment)."""
import json
from collections import defaultdict
from pathlib import Path

totals = defaultdict(lambda: {"calls": 0, "in": 0, "out": 0, "cost": 0.0, "latency": 0.0})
for line in Path("usage.jsonl").read_text().splitlines():
    entry = json.loads(line)
    row = totals[(entry["task"], entry["deployment"])]
    row["calls"] += 1
    row["in"] += entry["in"]
    row["out"] += entry["out"]
    row["cost"] += entry["cost_usd"]
    row["latency"] += entry["latency_s"]

print(f"{'task':<11}{'deployment':<24}{'calls':>6}{'tok in':>9}{'tok out':>9}{'avg s':>7}{'cost $':>10}")
for (task, deployment), r in sorted(totals.items()):
    print(f"{task:<11}{deployment:<24}{r['calls']:>6}{r['in']:>9}{r['out']:>9}"
          f"{r['latency'] / r['calls']:>7.2f}{r['cost']:>10.5f}")
