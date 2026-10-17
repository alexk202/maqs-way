"""Conditions gate (two outposts, per Lumín refinement 2026-10-17).

1. PRE-RUN (prereg self-consistency): every expectation line carrying a
   numeric range must bind it to a condition ('... under <condition>');
   a boundless range = RED before GPU is spent.
2. POST-RUN (measurement records): every results JSON must carry a
   `conditions` block per conditions-schema.json; missing block = RED.

Applies to NEW records. Existing evidence (prereg-v03.md lines written
before this gate) is grandfathered and stays as-is — appended addenda only,
no silent rewrites. Validator does NOT rewrite anything.

Usage:
  python3 evals/check_conditions.py --prereg evals/prereg-v03.md   # gate 1
  python3 evals/check_conditions.py --record evals/results/X.json  # gate 2
Exit 0 = green, non-zero = red.
"""
import json
import re
import sys
from pathlib import Path

REQUIRED = {"slice", "haystack", "n", "metric_type", "prereg_ref",
            "prereg_selection", "prereg_expectation"}
SEL = {"verified", "posthoc"}
EXP = {"verified", "mismatch", "posthoc"}
# Gate 1 scope: ONLY sections titled "## Expectations (bound)" are checked.
# Pre-gate-era sections (e.g. "Expected orders of magnitude (guess...)") are
# grandfathered — documented as pre-gate, never silently rewritten.
RANGE = re.compile(r"\[\s*[\d.]+\s*,\s*[\d.]+\s*\]")


def check_prereg(path: Path):
    lines = path.read_text().splitlines()
    bad, in_bound = [], False
    for i, line in enumerate(lines, 1):
        if line.startswith("## "):
            in_bound = line.strip() == "## Expectations (bound)"
            continue
        if in_bound and RANGE.search(line) and "under" not in line.lower():
            bad.append((i, line.strip()[:90]))
    return bad


def check_record(path: Path):
    d = json.loads(path.read_text())
    cond = d.get("conditions")
    if cond is None:
        return ["missing conditions block (post-run gate)"]
    errs = [f"missing field {k}" for k in REQUIRED if k not in cond]
    if "prereg_selection" in cond and cond["prereg_selection"] not in SEL:
        errs.append(f"bad prereg_selection {cond['prereg_selection']!r}")
    if "prereg_expectation" in cond and cond["prereg_expectation"] not in EXP:
        errs.append(f"bad prereg_expectation {cond['prereg_expectation']!r}")
    if not isinstance(cond.get("n", 0), int) or cond.get("n", 0) <= 0:
        errs.append("n must be positive int")
    return errs


def main() -> int:
    args = sys.argv[1:]
    if "--prereg" in args:
        bad = check_prereg(Path(args[args.index("--prereg") + 1]))
        for i, line in bad:
            print(f"GATE-RED prereg:{i}: range without bound condition — {line}")
        print(f"prereg self-consistency: {'RED' if bad else 'GREEN'} ({len(bad)} unbound)")
        return 1 if bad else 0
    if "--record" in args:
        errs = check_record(Path(args[args.index("--record") + 1]))
        for e in errs:
            print(f"GATE-RED record: {e}")
        print(f"record conditions: {'RED' if errs else 'GREEN'}")
        return 1 if errs else 0
    print("usage: check_conditions.py --prereg FILE | --record FILE")
    return 2


if __name__ == "__main__":
    sys.exit(main())