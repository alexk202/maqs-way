"""B write-integrity coverage gate (MAQS v1.8.1 B1-B6, Way package 1.2).

Rule: every MAQS write-integrity item must map to at least one Way rule
that REALLY EXISTS — either a principle P1-P8 in maqs-way-standard.json
or a closed-list non-principle section (LEGIT_NONP below), or a MAQS
item via the MAQS: prefix (validated against the local _MAQS mirror).

Three states (same stand as C8):
- covered: rules non-empty and all known  -> counts toward N/M
- known gap: rules empty BUT marked known_gap with owner + closes_in
  -> reported, does not fail
- uncovered: rules empty without marker, or unknown rule referenced -> RED

Locks on non-principle rules (council: three locks, no wildcards):
1. LEGIT_NONP is a closed versioned list in this script (like KNOWN_GAPS
   in the C8 gate) — adding a source is a code change, not silence.
2. Only concrete sections (e.g. "LOG-3.4"), never bare wildcards
   ("LOG" alone -> RED as unknown).
3. Each entry is verified against the document: LOG-3.4 requires
   the "logging" section to exist in maqs-way-standard.json.
MAQS: prefix validated against the local _MAQS mirror (mirrors
maqs_way_audit.MAQS_VALID; extension only by commit, never silently).

B4 probe (v0.3 step 9, signed docs/v0.3-canon/b4.md): check_b4_atomicity()
-- synthetic crash-point model, CPU-only, seconds, no external stores.
Probe boundary (owner amendment P1): logical crash-point model (synthetic
stores); OS-level durability (fsync, rename under power loss) not
exercised; proves the check distinguishes naive vs atomic writes,
certifies no system.

Run: python3 schemas/check_b_coverage.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "b_write_integrity.json"
STANDARD = ROOT / "maqs-way-standard.json"
SPEC_MANIFEST = ROOT / "schemas" / "spec-manifest.json"

# Closed whitelist (C8 pattern): ONLY these ids may be known gaps.
# B4 removed by v0.3 canonization (SPEC §2.5, owner signature 2026-10-27;
# rules MAQS:B4) — the gate's own prescription "remove it here AND in the
# fixture in one package" executed; a known_gap true entry is now a
# BYPASS attempt.
KNOWN_GAPS = set()

# Closed versioned list of legitimate non-principle rules.
# Key -> dotted path that must exist in maqs-way-standard.json.
LEGIT_NONP = {"LOG-3.4": "logging"}

# Local MAQS mirror for bare-token owners (mirrors check_c8_coverage.MAQS_VALID;
# consolidate in 1.8. Extension only by commit, never silently.)
# "B4" added in v0.3 step 9 (mirrors commit f548587).
_MAQS = {
    "0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "P",
    "E6", "F1", "F7", "G1", "I11", "B4",
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


B4_PROBE_BOUNDARY = ("B4 probe: logical crash-point model (synthetic stores); "
                     "OS-level durability (fsync, rename under power loss) "
                     "not exercised; proves the check distinguishes naive "
                     "vs atomic writes, certifies no system.")


def check_b4_atomicity():
    """B4 probe (v0.3 step 9, signed docs/v0.3-canon/b4.md).

    Synthetic crash-point model, CPU-only, seconds, no external stores.
    Probe boundary (owner amendment P1): logical crash-point model
    (synthetic stores); OS-level durability (fsync, rename under power
    loss) not exercised; proves the check distinguishes naive vs atomic
    writes, certifies no system.

    Model: two in-memory stores (a, b) + one real file + one paired state
    key. A write sequence is decomposed into steps; for EVERY point k the
    sequence is re-run with a crash after step k; after each crash a
    reader checks the observability invariant (fully-old or fully-new,
    never mixed), then recovery runs and the write is retried to
    convergence. The atomic implementation follows the canon semantics:
    intent record (in-progress) -> writes -> commit marker; readers treat
    uncommitted writes as absent (masked via the intent's backup);
    recovery rolls back uncommitted intents. The file part uses a temp
    file + atomic os.replace; the compound file+state pair flips under one
    commit marker; append is modeled as copy+rename.
    """
    fails = []
    old_v, new_v = "OLD", "NEW"
    f_old, f_new = "F-OLD", "F-NEW"
    half = "F-NE"

    def naive_reader(disk):
        return (disk["a"].get("v"), disk["b"].get("v"))

    def atomic_reader(disk):
        raw = (disk["a"].get("v"), disk["b"].get("v"))
        eff = list(raw)
        for it in disk["intents"]:
            for k, backup in it["backup"].items():
                eff[{"a": 0, "b": 1}[k]] = backup
        return tuple(eff)

    def task1_steps(kind):
        if kind == "naive":
            return [
                lambda d: d["a"].__setitem__("v", new_v),
                lambda d: d["b"].__setitem__("v", new_v),
            ]
        return [
            lambda d: d["intents"].append({"backup": {"a": d["a"].get("v"),
                                                      "b": d["b"].get("v")}}),
            lambda d: d["a"].__setitem__("v", new_v),
            lambda d: d["b"].__setitem__("v", new_v),
            lambda d: d["intents"].clear(),
        ]

    def atomic_recover(disk):
        for it in list(disk["intents"]):
            for k, backup in it["backup"].items():
                disk[k].__setitem__("v", backup)
        disk["intents"].clear()

    # Task 1: naive must produce a mixed observable state at some crash
    # point (that is the false safety B4 excludes); atomic must hold the
    # invariant at EVERY crash point and converge after recovery.
    naive_violated = False
    for k in range(2):
        d = {"a": {"v": old_v}, "b": {"v": old_v}, "intents": []}
        for i, st in enumerate(task1_steps("naive")):
            st(d)
            if i == k:
                break
        if naive_reader(d) != (old_v, old_v) and naive_reader(d) != (new_v, new_v):
            naive_violated = True
    if not naive_violated:
        fails.append("B4 probe: naive multi-store write never observed mixed "
                     "(probe cannot fail -> not a check)")
    for k in range(len(task1_steps("atomic"))):
        d = {"a": {"v": old_v}, "b": {"v": old_v}, "intents": []}
        for i, st in enumerate(task1_steps("atomic")):
            st(d)
            if i == k:
                break
        obs = atomic_reader(d)
        if obs not in ((old_v, old_v), (new_v, new_v)):
            fails.append(f"B4 probe: atomic multi-store mixed at crash point {k}: {obs}")
            continue
        atomic_recover(d)
        for st in task1_steps("atomic"):
            st(d)
        if atomic_reader(d) != (new_v, new_v):
            fails.append(f"B4 probe: atomic multi-store no convergence after crash point {k}")

    # Task 2: compound file+state pair + append semantics on a real file.
    # Naive: direct overwrite modeled as two sub-steps (half, rest) ->
    # crash after the first leaves a truncated file (observable neither
    # old nor new); crash between file and state leaves a mixed pair.
    # Atomic: intent (backup incl. file content) -> temp file -> atomic
    # os.replace -> state -> commit; readers mask uncommitted via the
    # intent backup; recovery restores the file content from the backup.
    def atomic_file_reader(disk):
        content = disk["file_path"].read_text()
        s = disk["s"].get("pair")
        for it in disk["intents"]:
            content = it["backup"].get("file", content)
            s = it["backup"].get("s", s)
        return (content, s)

    naive_file_violated = False
    for k in range(3):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "store.txt"
            fp.write_text(f_old)
            d = {"file_path": fp, "s": {"pair": "S-OLD"}, "intents": []}
            steps = [
                lambda d: d["file_path"].write_text(half),
                lambda d: d["file_path"].write_text(f_new),
                lambda d: d["s"].__setitem__("pair", "S-NEW"),
            ]
            for i, st in enumerate(steps):
                st(d)
                if i == k:
                    break
            obs = (fp.read_text(), d["s"].get("pair"))
            if obs != (f_old, "S-OLD") and obs != (f_new, "S-NEW"):
                naive_file_violated = True
    if not naive_file_violated:
        fails.append("B4 probe: naive file+state write never observed "
                     "truncated/mixed (probe cannot fail -> not a check)")
    a_steps = [
        lambda d: d["intents"].append({"backup": {"file": d["file_path"].read_text(),
                                                  "s": d["s"].get("pair")}}),
        lambda d: d.__setitem__("tmp", d["file_path"].with_suffix(".tmp")),
        lambda d: d["tmp"].write_text(f_new),
        lambda d: os.replace(str(d["tmp"]), str(d["file_path"])),
        lambda d: d["s"].__setitem__("pair", "S-NEW"),
        lambda d: d["intents"].clear(),
    ]
    for k in range(len(a_steps)):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "store.txt"
            fp.write_text(f_old)
            d = {"file_path": fp, "s": {"pair": "S-OLD"}, "intents": []}
            for i, st in enumerate(a_steps):
                st(d)
                if i == k:
                    break
            obs = atomic_file_reader(d)
            if obs != (f_old, "S-OLD") and obs != (f_new, "S-NEW"):
                fails.append(f"B4 probe: atomic file+state mixed at crash point {k}: {obs}")
                continue
            # recovery: restore file+state from the intent backup, clear it
            for it in list(d["intents"]):
                d["file_path"].write_text(it["backup"]["file"])
                d["s"].__setitem__("pair", it["backup"]["s"])
            d["intents"].clear()
            for st in a_steps:
                st(d)
            if atomic_file_reader(d) != (f_new, "S-NEW"):
                fails.append(f"B4 probe: atomic file+state no convergence after crash point {k}")

    # Compensation without an intent record = RED (the explicit in-progress
    # state is part of the requirement): after a crash right after the first
    # write, a 'recovery' with no backup info cannot restore the old state,
    # so the observable state stays mixed -- the variant is distinguished
    # as non-atomic.
    d = {"a": {"v": old_v}, "b": {"v": old_v}, "intents": []}
    d["a"]["v"] = new_v  # crash right after the first write
    if (d["a"].get("v"), d["b"].get("v")) in ((old_v, old_v), (new_v, new_v)):
        fails.append("B4 probe: compensation-without-intent not distinguished")

    for f in fails:
        print(f"GATE RED — {f}")
    print(B4_PROBE_BOUNDARY)
    return 1 if fails else 0


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
        bad = [r for r in rules if r not in known and r not in LEGIT_NONP
               and not (r.startswith("MAQS:") and r[5:] in _MAQS)]
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
    if check_b4_atomicity() != 0:
        print("GATE RED")
        return 1
    if gaps:
        print("GATE GREEN with known gap(s) — see owners above")
    else:
        print("GATE GREEN — full coverage")
    return 0


if __name__ == "__main__":
    sys.exit(main())
