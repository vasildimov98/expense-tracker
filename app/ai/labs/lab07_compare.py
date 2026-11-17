"""Compare two evaluation runs row by row (Lab 7 Task 4 step 4).

Run: python -m app.ai.labs.lab07_compare A2 B
Only rows scored in BOTH runs count (D75); judge noise is about +-1, so look for drops of 2 or more.
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).parent
a_label, b_label = sys.argv[1], sys.argv[2]


def load(label):
    return json.loads((HERE / f"lab07_eval_{label}.json").read_text())["rows"]


def score(row, metric):
    v = row.get(f"outputs.{metric}.{metric}")
    return v if isinstance(v, (int, float)) and v == v else None


a_rows, b_rows = load(a_label), load(b_label)
by_kind = defaultdict(lambda: defaultdict(list))
print(f"{'kind':12} {'g ' + a_label:>6} {'g ' + b_label:>6} {'r ' + a_label:>6} {'r ' + b_label:>6}  query")
for a, b in zip(a_rows, b_rows):
    assert a["inputs.query"] == b["inputs.query"], "the two runs must use the same dataset order"
    cells = []
    for metric in ("groundedness", "relevance"):
        sa, sb = score(a, metric), score(b, metric)
        cells += [sa, sb]
        if sa is not None and sb is not None:
            by_kind[a["inputs.kind"]][metric].append(sb - sa)
    flag = "  <-- DROP" if any(
        x is not None and y is not None and y - x <= -2 for x, y in ((cells[0], cells[1]), (cells[2], cells[3]))) else ""
    fmt = lambda v: "  -  " if v is None else f"{v:5.1f}"
    print(f"{a['inputs.kind']:12} {fmt(cells[0])} {fmt(cells[1])} {fmt(cells[2])} {fmt(cells[3])}  {a['inputs.query'][:50]}{flag}")

print(f"\nmean change by kind ({b_label} minus {a_label}), complete rows only")
for kind, metrics in by_kind.items():
    print(f"  {kind:12} " + "  ".join(f"{m}={sum(v) / len(v):+.2f} (n={len(v)})" for m, v in metrics.items()))
