"""C8 traceback-coverage gate (MAQS v1.6 C8, Way package).

Rule: every failure class observed in production must map to at least one
Way rule (P1-P8) that REALLY EXISTS in maqs-way-standard.json. A class with
zero coverage is a gap.

Three states (Lumik: gate must tell them apart):
- covered: rules non-empty and all known  -> counts toward N/M
- known gap: rules empty BUT marked known_gap with owner + closes_in
  (bridge tracker, e.g. C8 -> I11 -> package 1.6) -> reported, does not fail
- uncovered: rules empty without marker, or unknown rule referenced -> RED

Report is honest: "N/M covered + K known gap(s)". Never "all green" while
a gap exists without an owner.

Run: python3 schemas/check_c8_coverage.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "c8_classes.json"
STANDARD = ROOT / "maqs-way-standard.json"


def main() -> int:
    classes = json.loads(FIXTURE.read_text())
    standard = json.loads(STANDARD.read_text())
    known = {p["id"] for p in standard["principles"]}

    covered, gaps, reds, unknowns = [], [], [], []
    for c in classes:
        rules = c.get("rules", [])
        if not rules:
            if c.get("known_gap") and c.get("owner") and c.get("closes_in"):
                gaps.append(c)
            else:
                reds.append(c["id"])
            continue
        bad = [r for r in rules if r not in known]
        if bad:
            unknowns.append((c["id"], bad))
        else:
            covered.append(c["id"])

    print(f"COVERED {len(covered)}/{len(classes)}: {', '.join(covered)}")
    for g in gaps:
        print(
            f"KNOWN GAP: {g['id']} (maqs {g.get('maqs')}) "
            f"-> owner {g['owner']}, closes in {g['closes_in']}"
        )
    for cid, bad in unknowns:
        print(f"UNKNOWN RULES in {cid}: {', '.join(bad)}")
    for cid in reds:
        print(f"UNCOVERED (no owner): {cid}")

    if reds or unknowns:
        print("GATE RED")
        return 1
    if gaps:
        print("GATE GREEN with known gap(s) — see owners above")
    else:
        print("GATE GREEN — full coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
