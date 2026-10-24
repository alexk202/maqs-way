"""C8 traceback-coverage gate (MAQS v1.6 C8, Way package).

Rule: every failure class observed in production must map to at least one
Way rule (P1-P8) that REALLY EXISTS in maqs-way-standard.json. A class with
zero coverage is a gap.

Three states (council: gate must tell them apart):
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
SPEC_MANIFEST = ROOT / "schemas" / "spec-manifest.json"

# Closed whitelist (council control): ONLY these ids may be known gaps.
# Any other class marked known_gap is a bypass attempt -> RED.
# Bridge consolidation (package 1.6a): a gap entry WITH anchor rules is
# BRIDGED (subject moved to the owning formulation), NOT covered and NOT
# closed — I11 stays a gap until v0.2 canonization. Covered count MUST NOT
# absorb bridged entries (no false green).
KNOWN_GAPS = {"recovery_loop_without_diagnosis"}

# Local MAQS namespace mirror (CLI maqs_way_audit.py holds its own copy;
# consolidate in 1.8. Extension only by commit, never silently.)
MAQS_VALID = {
    "0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "P",
    "E6", "F1", "F7", "G1", "I11",
}
LEGIT_NONP = {"LOG-3.4": "logging"}


def _resolve_owner(owner, sections, principles):
    """True iff owner resolves: SPEC-style to manifest sections, else bare
    token to principles / MAQS_VALID / LEGIT_NONP. Free-text otherwise."""
    if not isinstance(owner, str) or not owner.strip():
        return False
    o = owner.strip()
    for prefix in ("SPEC §", "SPEC ", "§"):
        if o.startswith(prefix):
            return o[len(prefix):].strip().rstrip(".") in sections
    parts = [p.strip() for p in o.split(",")]
    return all(p in principles or p in MAQS_VALID or p in LEGIT_NONP
               for p in parts)


def main() -> int:
    classes = json.loads(FIXTURE.read_text())
    standard = json.loads(STANDARD.read_text())
    manifest = json.loads(SPEC_MANIFEST.read_text())
    known = {p["id"] for p in standard["principles"]}
    sections = set(manifest.get("sections", []))

    # Version lockstep: manifest must track the release stamp, else it rots.
    if manifest.get("version") != standard.get("version"):
        print(f"GATE RED — spec-manifest {manifest.get('version')} != standard {standard.get('version')}")
        return 1

    # Lockstep guard (adversarial control): the whitelist and the fixture must
    # name EXACTLY the same set — no silent growth on either side.
    fixture_gaps = {c["id"] for c in classes if c.get("known_gap")}
    if fixture_gaps != KNOWN_GAPS:
        print(f"GATE RED — whitelist/fixture mismatch:")
        print(f"  whitelist ({len(KNOWN_GAPS)}): {sorted(KNOWN_GAPS)}")
        print(f"  fixture   ({len(fixture_gaps)}): {sorted(fixture_gaps)}")
        return 1

    covered, gaps, bridged, reds, unknowns, bypass, dangling = [], [], [], [], [], [], []
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
        bad = [r for r in rules if r not in known and r not in LEGIT_NONP
               and not (r.startswith("MAQS:") and r[5:] in MAQS_VALID)]
        if bad:
            unknowns.append((c["id"], bad))
        elif c.get("known_gap") and c["id"] in KNOWN_GAPS:
            bridged.append(c)
        else:
            covered.append(c["id"])

    print(f"COVERED {len(covered)}/{len(classes)}: {', '.join(covered)}")
    for g in gaps:
        print(
            f"KNOWN GAP: {g['id']} (maqs {g.get('maqs')}) "
            f"-> owner {g['owner']}, closes in {g['closes_in']}"
        )
    for g in bridged:
        print(
            f"BRIDGED (not covered, not closed): {g['id']} (maqs {g.get('maqs')}) "
            f"-> consolidated to {g.get('owner')}, closes in {g.get('closes_in')}; "
            f"anchor rules: {', '.join(g.get('rules', []))}"
        )
    for cid, bad in unknowns:
        print(f"UNKNOWN RULES in {cid}: {', '.join(bad)}")
    for cid in reds:
        print(f"UNCOVERED (no owner): {cid}")
    for cid in bypass:
        print(f"BYPASS ATTEMPT (known_gap not in whitelist): {cid}")
    for g in gaps + bridged:
        if not _resolve_owner(g.get("owner"), sections, known):
            dangling.append((g["id"], g.get("owner")))
    for cid, owner in dangling:
        print(f"DANGLING OWNER in {cid}: {owner!r} resolves to nothing (SPEC manifest / MAQS / principles)")
    targets = manifest.get("release_targets", [])
    dangling_targets = [(g["id"], g.get("closes_in")) for g in gaps + bridged
                        if not any(t in (g.get("closes_in") or "") for t in targets)]
    for cid, ci in dangling_targets:
        print(f"DANGLING closes_in in {cid}: {ci!r} matches no release_targets {targets}")

    if reds or unknowns or bypass or dangling or dangling_targets:
        print("GATE RED")
        return 1
    if gaps and bridged:
        print("GATE GREEN with known gap(s) + bridged gap(s) — see owners above")
    elif gaps:
        print("GATE GREEN with known gap(s) — see owners above")
    elif bridged:
        print("GATE GREEN with bridged gap(s) — consolidated, not closed; see above")
    else:
        print("GATE GREEN — full coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
