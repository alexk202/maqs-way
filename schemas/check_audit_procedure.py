"""P9/P10 audit-procedure gate (Way package 1.7a).

Formulation lives in proposals/p9-p10-audit.md (historical only;
normative text is in SPEC §3.5, canonized v0.3, owner signature 2026-10-27).

P9: evaluate() is one-sided — positive = proof, negative = inconclusive
(never pass). One-sidedness is declared upfront in every report.
P10: snapshot-run-verify on the LIVE repo — snapshot `git status --porcelain`
(including untracked), run all gates, verify identical. A gate writing
into the repo (modification OR new file) fails P10.

CLI integration point (documented, not implemented): `audit procedure`
after v0.2 canonization. CLI 1.4 and gates 1.1–1.6d untouched.

Run: python3 schemas/check_audit_procedure.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "audit_procedure.json"

# Closed whitelist: ONLY these ids may be known gaps. P9/P10 closed by
# v0.3 canonization (SPEC §3.5, owner signature 2026-10-27; rules
# MAQS:P9/MAQS:P10 per owner amendment -- no new namespace token).
KNOWN_GAPS = set()

# Rule namespaces for covered entries: local mirror of maqs_way_audit.MAQS_VALID
# (extended with P9/P10 in commit 3465361) + LOG-3.4 (existing token).
MAQS_VALID = {
    "0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "P",
    "E6", "F1", "F7", "G1", "I11", "P9", "P10",
}
LEGIT_NONP = {"LOG-3.4": "logging"}

GATES = [
    "schemas/check_conformance.py",
    "schemas/check_b_coverage.py",
    "schemas/check_c8_coverage.py",
    "schemas/check_i13_redaction.py",
    "schemas/check_e_assembly.py",
    "schemas/check_i_counters.py",
    "schemas/check_i_handlers.py",
    "schemas/check_i_layers.py",
]


def evaluate(probe, outcome):
    """One-sided: positive -> proof; negative -> inconclusive (never pass)."""
    if outcome in ("fired", "found", "retrieved", "mentioned", "appeared"):
        return "proof"
    return "inconclusive"


def snapshot():
    r = subprocess.run(["git", "status", "--porcelain"], capture_output=True,
                       text=True, cwd=ROOT)
    if r.returncode != 0:
        # fail-closed: a vacuous "" == "" comparison would let probe2 pass
        # even when git is unavailable (same class as the name-policy finding)
        return None
    return r.stdout


def check_fixture():
    classes = json.loads(FIXTURE.read_text())
    fixture_gaps = {c["id"] for c in classes if c.get("known_gap")}
    if fixture_gaps != KNOWN_GAPS:
        print("GATE RED — whitelist/fixture mismatch:")
        print(f"  whitelist ({len(KNOWN_GAPS)}): {sorted(KNOWN_GAPS)}")
        print(f"  fixture   ({len(fixture_gaps)}): {sorted(fixture_gaps)}")
        return 1
    for c in classes:
        if not c.get("rules"):
            if not (c["id"] in KNOWN_GAPS and c.get("known_gap")
                    and c.get("owner") and c.get("closes_in")
                    and c.get("formulation")):
                print(f"GATE RED — malformed gap entry: {c.get('id')}")
                return 1
            form = c["formulation"].split("#")[0]
            if not (ROOT / form).exists():
                print(f"GATE RED — orphan formulation ref in {c['id']}")
                return 1
            print(f"KNOWN GAP: {c['id']} (maqs {c.get('maqs')}) "
                  f"-> owner {c['owner']}, closes in {c['closes_in']}")
        elif c.get("known_gap"):
            print(f"BYPASS ATTEMPT (known_gap not in whitelist): {c['id']}")
            print("GATE RED")
            return 1
        else:
            standard = json.loads((ROOT / "maqs-way-standard.json").read_text())
            known_way = {p["id"] for p in standard["principles"]}
            bad = [r for r in c.get("rules", [])
                   if r not in known_way and r not in LEGIT_NONP
                   and not (r.startswith("MAQS:") and r[5:] in MAQS_VALID)]
            if bad:
                print(f"UNKNOWN RULES in {c['id']}: {', '.join(bad)}")
                print("GATE RED")
                return 1
            print(f"COVERED: {c['id']} (canonized v0.3 → SPEC §3.5)")
    return 0


def check_semantics():
    fails = []

    # Probe 1: negative-as-pass is RED (evaluate must never return pass).
    for outcome in ("not_found", "absent", "silent", "timeout"):
        if evaluate("canary", outcome) != "inconclusive":
            fails.append(f"probe1 negative-as-{outcome} not inconclusive")
    if evaluate("canary", "retrieved") != "proof":
        fails.append("probe1 positive not proof")
    # The word "pass" must never leave evaluate().
    for outcome in ("fired", "found", "not_found", "absent"):
        if evaluate("decoy", outcome) == "pass":
            fails.append("probe1 evaluate emitted pass")

    # Probe 2: P10 read-only on the live repo (tracked AND untracked).
    before = snapshot()
    if before is None:
        fails.append("probe2 git status unavailable (fail-closed)")
    for g in GATES:
        r = subprocess.run([sys.executable, str(ROOT / g)],
                           capture_output=True, text=True, cwd=ROOT)
        if r.returncode != 0:
            fails.append(f"probe2 gate failed live: {g}")
    after = snapshot()
    if after is None:
        fails.append("probe2 git status unavailable after gates (fail-closed)")
    elif before != after:
        fails.append("probe2 auditor wrote to repo (tracked or untracked)")

    for f in fails:
        print(f"GATE RED — {f}")
    return 1 if fails else 0


def main() -> int:
    if check_fixture() != 0:
        return 1
    if check_semantics() != 0:
        print("GATE RED")
        return 1
    print("COVERED 2/2 + KNOWN GAPS 0 (P9, P10 canonized v0.3 → SPEC §3.5)")
    print("ONE-SIDED declared upfront: negative = inconclusive; coverage NOT claimed")
    print("P10 read-only verified by fact (snapshot incl. untracked, identical)")
    print("GATE GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
