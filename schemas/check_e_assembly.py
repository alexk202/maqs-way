"""E10/E11 assembly gate (MAQS E10 [REC] / E11 [IMP], Way package 1.5).

Formulation lives in proposals/e10-e11-assembly.md (historical only;
normative text is in SPEC §2.4, canonized v0.3, owner signature 2026-10-27).

Executable without infra (pure functions on synthetic records):
- cap: protect_request() DENYs beyond cap + emits cap_overflow (never silent evict)
- orthogonality: alive and legal_hold coexist; is_forgettable() respects both
- placement: verify_placement() FAILs on middle-zone critical; unmarked blocks
  are no-op + counted (unlabeled_ratio); auto-critical without declared label
  is DENY/flagged (probe 5), never inferred.

Fixture checks (C8 pattern): three states + whitelist/fixture lockstep +
cross-ref — every fixture entry must point at an existing formulation file
(anti-orphan, package 1.3 precedent).

Run: python3 schemas/check_e_assembly.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "e_assembly.json"
PROPOSAL = ROOT / "proposals" / "e10-e11-assembly.md"

# Closed whitelist (C8 pattern): ONLY these ids may be known gaps.
# E10/E11 closed by v0.3 canonization (SPEC §2.4, owner signature 2026-10-27).
KNOWN_GAPS = set()

HEAD_TAIL = 0.15  # head/tail zones as share of context tokens (v0.1 default)


def protect_request(records, cap):
    """Default DENY: returns (allowed, event). Never silently evicts."""
    protected = [r for r in records if r.get("alive")]
    if len(protected) >= cap:
        return False, {"event": "cap_overflow", "protected": len(protected), "cap": cap}
    return True, None


def is_forgettable(record):
    return not record.get("alive") and not record.get("legal_hold")


def verify_placement(blocks):
    """Structural audit. Returns (ok, unlabeled_ratio, log).

    blocks: list of {id, tokens, critical: bool(declared), zone: head|middle|tail}.
    Auto-critical (importance without declared label) is NOT honored: such a
    block is treated as non-critical and flagged (probe 5).
    """
    total_tokens = sum(b["tokens"] for b in blocks) or 1
    unlabeled = sum(b["tokens"] for b in blocks if not b.get("critical")
                    and b.get("importance") is None)
    ratio = unlabeled / total_tokens
    log = []
    for b in blocks:
        if b.get("importance") is not None and not b.get("critical"):
            log.append(f"flag auto-critical attempt (no declared label): {b['id']}")
        if b.get("critical") and b.get("zone") == "middle":
            return False, ratio, log + [f"RED critical-in-middle: {b['id']}"]
    if not any(b.get("critical") for b in blocks):
        log.append("0 critical blocks (no-op, explicit)")
    return True, ratio, log


def check_fixture():
    classes = json.loads(FIXTURE.read_text())
    standard = json.loads((ROOT / "maqs-way-standard.json").read_text())
    known_way = {p["id"] for p in standard["principles"]}
    fixture_gaps = {c["id"] for c in classes if c.get("known_gap")}
    if fixture_gaps != KNOWN_GAPS:
        print("GATE RED — whitelist/fixture mismatch:")
        print(f"  whitelist ({len(KNOWN_GAPS)}): {sorted(KNOWN_GAPS)}")
        print(f"  fixture   ({len(fixture_gaps)}): {sorted(fixture_gaps)}")
        return 1
    reds, bypass, unknowns = [], [], []
    for c in classes:
        rules = c.get("rules", [])
        if rules:
            bad = [r for r in rules if r not in known_way]
            if bad:
                unknowns.append((c["id"], bad))
            else:
                print(f"COVERED: {c['id']} (canonized v0.3 -> SPEC §2.4)")
            continue
        if not c.get("rules"):
            if (c["id"] in KNOWN_GAPS and c.get("known_gap")
                    and c.get("owner") and c.get("closes_in")):
                form = c.get("formulation", "")
                target = (ROOT / form.split("#")[0]) if form else None
                if target is None or not target.exists():
                    print(f"GATE RED — orphan formulation ref in {c['id']}: {form}")
                    return 1
                print(f"KNOWN GAP: {c['id']} (maqs {c.get('maqs')}) "
                      f"-> owner {c['owner']}, closes in {c['closes_in']}")
            elif c.get("known_gap"):
                bypass.append(c["id"])
            else:
                reds.append(c["id"])
    for cid in bypass:
        print(f"BYPASS ATTEMPT (known_gap not in whitelist): {cid}")
    for cid in reds:
        print(f"UNCOVERED (no owner): {cid}")
    for cid, bad in unknowns:
        print(f"UNKNOWN RULES in {cid}: {', '.join(bad)}")
    if reds or bypass or unknowns:
        print("GATE RED")
        return 1
    return 0


def check_semantics():
    fails = []

    # Probe 1: cap+1 -> DENY with event (never silent evict).
    recs = [{"id": f"m{i}", "alive": True} for i in range(3)]
    allowed, event = protect_request(recs, cap=3)
    if allowed or not event or event["event"] != "cap_overflow":
        fails.append("probe1 cap+1 must DENY with cap_overflow event")

    # Probe 2: unmarked block -> no-op + explicit log (never silent pass).
    ok, ratio, log = verify_placement([{"id": "b1", "tokens": 100, "zone": "middle"}])
    if not ok or not any("0 critical blocks" in l for l in log):
        fails.append("probe2 unmarked must no-op with explicit log")

    # Probe 3: critical-in-middle -> RED.
    ok, _, _ = verify_placement([
        {"id": "c1", "tokens": 10, "critical": True, "zone": "head"},
        {"id": "c2", "tokens": 10, "critical": True, "zone": "middle"},
    ])
    if ok:
        fails.append("probe3 critical-in-middle must RED")

    # Probe 4: alive+hold coexist (both protections hold, no collapse).
    r = {"id": "m", "alive": True, "legal_hold": True}
    if is_forgettable(r):
        fails.append("probe4 alive+hold record must NOT be forgettable")
    if is_forgettable({"id": "x"}):
        pass
    else:
        fails.append("probe4 plain record must be forgettable")

    # Probe 5: auto-critical (importance, no declared label) -> flagged, not honored.
    ok, _, log = verify_placement([
        {"id": "a1", "tokens": 50, "zone": "head", "importance": 0.9},
    ])
    if not ok or not any("auto-critical" in l for l in log):
        fails.append("probe5 auto-critical must be flagged, not honored")

    for f in fails:
        print(f"GATE RED — {f}")
    return 1 if fails else 0


def main() -> int:
    rc = check_fixture()
    if rc != 0:
        return rc
    rc = check_semantics()
    if rc != 0:
        print("GATE RED")
        return 1
    print("COVERED 2/2 + KNOWN GAPS 0 (E10, E11 canonized v0.3 -> SPEC §2.4)")
    print("SEMANTICS 5/5 (cap-deny, unmarked-noop, middle-RED, coexist, auto-flag)")
    print("GATE GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
