#!/usr/bin/env python3
"""
Leaderboard probes: one submission per disputed decision of the model.

Every variant differs from `base` in exactly one decision, so the difference
between two leaderboard scores is the verdict on that decision.
Output: submissions/variants/<name>.jsonl + submissions/variants/README.md
"""

import contextlib
import io
import json
import re
from collections import Counter
from pathlib import Path

from solve_dabstep import ROOT, DABstepBSLSolver, run_all

VARIANTS = [
    ("base", {}, "model as is: fraud level by volume, matched rules summed, rule-less payments cost 0"),
    ("fraud-count", {"fraud_basis": "count"}, "monthly fraud level = fraudulent tx count / tx count"),
    ("agg-mean", {"agg": "mean"}, "total fee: average of the matched rules instead of their sum"),
    ("agg-min", {"agg": "min"}, "total fee: cheapest matched rule instead of the sum"),
    ("agg-first", {"agg": "first"}, "total fee: matched rule with the lowest ID instead of the sum"),
    ("aci-min", {"aci_agg": "min"}, "move-fraud-to-ACI: cheapest matched rule instead of the sum"),
    ("uncovered-exclude", {"uncovered": "exclude"}, "what-if scheme / ACI that leaves a payment without a rule is not a candidate"),
]

FAMILIES = [
    ("applicable fee IDs", r"[Ff]ee IDs"),
    ("total fees", r"total fees"),
    ("rate-change delta", r"relative fee of the fee with ID"),
    ("MCC-change delta", r"changed its MCC code"),
    ("affected merchants", r"affected by"),
    ("steer to card scheme", r"steer traffic"),
    ("move fraud to ACI", r"move the fraudulent transactions"),
]


def family(q: str) -> str:
    for name, pat in FAMILIES:
        if re.search(pat, q):
            return name
    return "other"


def main() -> None:
    out_dir = ROOT / "submissions" / "variants"
    tasks = {}
    with open(ROOT / "data" / "tasks" / "all.jsonl", encoding="utf-8") as f:
        for line in f:
            t = json.loads(line)
            tasks[str(t["task_id"])] = t

    answers = {}
    for name, kwargs, _ in VARIANTS:
        path = out_dir / f"{name}.jsonl"
        with contextlib.redirect_stdout(io.StringIO()):
            run_all(DABstepBSLSolver(**kwargs), path)
        with open(path, encoding="utf-8") as f:
            answers[name] = {r["task_id"]: r["agent_answer"] for r in map(json.loads, f)}

    base = answers["base"]
    lines = [
        "# Submission variants",
        "",
        "Each file differs from `base.jsonl` in one decision. Submit `base` first;",
        "the score difference of any other file against it is the verdict on that decision.",
        "The last column is the largest possible score change (tasks whose answer differs).",
        "",
        "| File | Decision | Answers changed | By task family |",
        "|---|---|---|---|",
    ]
    for name, _, desc in VARIANTS:
        diff = [tid for tid in base if answers[name][tid] != base[tid]]
        fam = Counter(family(tasks[tid]["question"]) for tid in diff)
        fam_s = ", ".join(f"{k} {v}" for k, v in fam.most_common()) or "—"
        lines.append(f"| `{name}.jsonl` | {desc} | {len(diff)} | {fam_s} |")
        print(f"{name:18s} changed={len(diff):3d}  {fam_s}")
    (out_dir / "README.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
