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

# Closed whitelist (Prima control): ONLY these ids may be known gaps.
# Any other class marked known_gap is a bypass attempt -> RED.
# When I11 closes the gap, remove it here AND in the fixture in one package.
KNOWN_GAPS = {"recovery_loop_without_diagnosis"}


def main() -> int:
    classes = json.loads(FIXTURE.read_text())
    standard = json.loads(STANDARD.read_text())
    known = {p["id"] for p in standard["principles"]}

    # Lockstep guard (adversarial control): the whitelist and the fixture must
    # name EXACTLY the same set — no silent growth on either side.
    fixture_gaps = {c["id"] for c in classes if c.get("known_gap")}
    if fixture_gaps != KNOWN_GAPS:
        print(f"GATE RED — whitelist/fixture mismatch:")
        print(f"  whitelist ({len(KNOWN_GAPS)}): {sorted(KNOWN_GAPS)}")
        print(f"  fixture   ({len(fixture_gaps)}): {sorted(fixture_gaps)}")
        return 1

    covered, gaps, reds, unknowns, bypass = [], [], [], [], []
    for c in classes:
        rules = c.get("rules", [])
        if not rules:
            if (
                c["id"] in KNOWN_GAPS
                and c.get("known_gap")
                and c.get("owner")
                and c.get("closes_in")
            ):
                gaps.append(c)
            elif c.get("known_gap"):
                bypass.append(c["id"])
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
    for cid in bypass:
        print(f"BYPASS ATTEMPT (known_gap not in whitelist): {cid}")

    if reds or unknowns or bypass:
        print("GATE RED")
        return 1
    if gaps:
        print("GATE GREEN with known gap(s) — see owners above")
    else:
        print("GATE GREEN — full coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
