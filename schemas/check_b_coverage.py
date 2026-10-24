"""B write-integrity coverage gate (MAQS v1.6 B1-B6, Way package 1.2).

Rule: every MAQS write-integrity item must map to at least one Way rule
that REALLY EXISTS — either a principle P1-P8 in maqs-way-standard.json
or a closed-list non-principle section (LEGIT_NONP below).

Three states (same stand as C8):
- covered: rules non-empty and all known  -> counts toward N/M
- known gap: rules empty BUT marked known_gap with owner + closes_in
  (bridge tracker, e.g. B4 -> new write-atomicity requirement in v0.2)
  -> reported, does not fail
- uncovered: rules empty without marker, or unknown rule referenced -> RED

Locks on non-principle rules (council: three locks, no wildcards):
1. LEGIT_NONP is a closed versioned list in this script (like KNOWN_GAPS
   in the C8 gate) — adding a source is a code change, not silence.
2. Only concrete sections (e.g. "LOG-3.4"), never bare wildcards
   ("LOG" alone -> RED as unknown).
3. Each entry is verified against the document: LOG-3.4 requires
   the "logging" section to exist in maqs-way-standard.json.

Run: python3 schemas/check_b_coverage.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "b_write_integrity.json"
STANDARD = ROOT / "maqs-way-standard.json"
SPEC_MANIFEST = ROOT / "schemas" / "spec-manifest.json"

# Closed whitelist (C8 pattern): ONLY these ids may be known gaps.
# Any other item marked known_gap is a bypass attempt -> RED.
# When the write-atomicity requirement lands in §2.5 (v0.2),
# remove it here AND in the fixture in one package.
KNOWN_GAPS = {"B4"}

# Closed versioned list of legitimate non-principle rules.
# Key -> dotted path that must exist in maqs-way-standard.json.
LEGIT_NONP = {"LOG-3.4": "logging"}

# Local MAQS mirror for bare-token owners (mirrors check_c8_coverage.MAQS_VALID;
# consolidate in 1.8. Extension only by commit, never silently.)
_MAQS = {
    "0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "P",
    "E6", "F1", "F7", "G1", "I11",
}


def _resolve_owner(owner, sections, principles):
    """True iff owner resolves: SPEC-style to manifest sections, else bare
    token to principles / MAQS / LEGIT_NONP. Free-text otherwise -> dangling."""
    if not isinstance(owner, str) or not owner.strip():
        return False
    o = owner.strip()
    for prefix in ("SPEC §", "SPEC ", "§"):
        if o.startswith(prefix):
            return o[len(prefix):].strip().rstrip(".") in sections
    parts = [p.strip() for p in o.split(",")]
    return all(p in principles or p in _MAQS or p in LEGIT_NONP for p in parts)


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

    # Lock 3: every LEGIT_NONP entry must resolve against the document.
    for rule, path in LEGIT_NONP.items():
        node = standard
        for part in path.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            print(f"GATE RED — legit rule {rule} has no target '{path}' in standard")
            return 1

    # Lockstep guard (adversarial control): the whitelist and the fixture must
    # name EXACTLY the same set — no silent growth on either side.
    fixture_gaps = {c["id"] for c in classes if c.get("known_gap")}
    if fixture_gaps != KNOWN_GAPS:
        print("GATE RED — whitelist/fixture mismatch:")
        print(f"  whitelist ({len(KNOWN_GAPS)}): {sorted(KNOWN_GAPS)}")
        print(f"  fixture   ({len(fixture_gaps)}): {sorted(fixture_gaps)}")
        return 1

    covered, gaps, reds, unknowns, bypass, dangling = [], [], [], [], [], []
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
        bad = [r for r in rules if r not in known and r not in LEGIT_NONP]
        if bad:
            unknowns.append((c["id"], bad))
        else:
            covered.append(c["id"])

    print(f"COVERED {len(covered)}/{len(classes)}: {', '.join(covered)}")
    for g in gaps:
        adj = f" (adjacent, not covering: {', '.join(g.get('adjacent', []))})" if g.get("adjacent") else ""
        print(
            f"KNOWN GAP: {g['id']} (maqs {g.get('maqs')}){adj} "
            f"-> owner {g['owner']}, closes in {g['closes_in']}"
        )
    for cid, bad in unknowns:
        print(f"UNKNOWN RULES in {cid}: {', '.join(bad)}")
    for cid in reds:
        print(f"UNCOVERED (no owner): {cid}")
    for cid in bypass:
        print(f"BYPASS ATTEMPT (known_gap not in whitelist): {cid}")
    for g in gaps:
        if not _resolve_owner(g.get("owner"), sections, known):
            dangling.append((g["id"], g.get("owner")))
    for cid, owner in dangling:
        print(f"DANGLING OWNER in {cid}: {owner!r} resolves to nothing (SPEC manifest / MAQS / principles)")
    targets = manifest.get("release_targets", [])
    dangling_targets = [(g["id"], g.get("closes_in")) for g in gaps
                        if not any(t in (g.get("closes_in") or "") for t in targets)]
    for cid, ci in dangling_targets:
        print(f"DANGLING closes_in in {cid}: {ci!r} matches no release_targets {targets}")

    if reds or unknowns or bypass or dangling or dangling_targets:
        print("GATE RED")
        return 1
    if gaps:
        print("GATE GREEN with known gap(s) — see owners above")
    else:
        print("GATE GREEN — full coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
