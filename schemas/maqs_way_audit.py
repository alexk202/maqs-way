"""MAQS-Way audit CLI v0.1 (Way package 1.4).

CLI is a facade over existing gates (1.1-1.3 artifacts imported, not modified).
Edits to existing gate modules = separate package, not 1.4.

Namespace scheme: established by owner decision sanction-1.4-2026-10-14.
1.4 applies it in manifest + CLI validation, does not re-establish.
- Way:<P>      -> principle id in maqs-way-standard.json (bare "P<n>" = Way shorthand)
- MAQS:<ref>   -> closed list below (governed-by-code: extensions only by commit
                 with rationale in message, never silently; cf. KNOWN_GAPS 740c304)
- LOG-<sec>    -> closed map below (e.g. LOG-3.4 -> logging section)
- SCHEMA:<name> -> file schemas/<name> exists
Bare "LOG-3.4" (1.2 form) accepted as documented shorthand.

Canon-pin v0.1: single pin (005.similarity_threshold == 0.3, SPEC §3.3 line 241).
Extension point: add entries to PINS when a second canon-anchored number appears
in vectors. Do not generalize before a second real case exists (J1);
generalize at >= 3 pins.
The pin READS the canon at run time (SPEC.md parsed, not a duplicated constant):
canon source missing/unparseable -> RED, not skip.

Usage:
  python3 schemas/maqs_way_audit.py [schema|manifest|lint|coverage|all|namespaces|pin|replay|scoreboard]
      [--format text|json]
Exit 0 = green, 1 = red.
"""
import argparse
import contextlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "schemas"))

import check_b_coverage
import check_c8_coverage
import check_conformance
import check_scoreboard
import replay_vectors

STANDARD = ROOT / "maqs-way-standard.json"
SPEC = ROOT / "SPEC.md"
MANIFEST = ROOT / "conformance" / "manifest.json"
PIN_VECTOR = ROOT / "conformance" / "invalid" / "005-shared-fact-visibility-leak.json"

# Closed MAQS namespace list (governed-by-code, see module docstring).
# Sections 0,A-K,P verified against MAQS STANDARD (Sections 0,J,K present);
# item refs cover actual usage: E6 (P1 mapping), F7 (invalid-002), G1 (G1 fixtures),
# I11 (C8->I11 bridge, commit 7db1dd7).
MAQS_VALID = {
    "0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "P",
    "E6", "F1", "F7", "G1", "I11",
}

# Closed LOG namespace map: rule suffix -> dotted path in maqs-way-standard.json.
LOG_VALID = {"LOG-3.4": "logging"}

# Canon pins: vector file -> (json path in vector, canon section regex, canon file).
PINS = {
    "invalid-005": {
        "vector": str(PIN_VECTOR.relative_to(ROOT)),
        "field": "fixture.similarity_threshold",
        "canon_file": "SPEC.md",
        "canon_pattern": r"SEMANTIC:\s*embedding similarity\s*<\s*(\d+(?:\.\d+)?)",
    },
}


def _get_path(doc, dotted):
    node = doc
    for part in dotted.split("."):
        node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            return None
    return node


def check_namespaces():
    """Validate every rule ref in manifest + B/C8 fixtures against its source."""
    standard = json.loads(STANDARD.read_text())
    known_way = {p["id"] for p in standard["principles"]}
    bad = []

    def check_ref(ref, where):
        if ref in known_way:  # bare-P Way shorthand (documented)
            return
        if ref.startswith("Way:"):
            if ref[4:] not in known_way:
                bad.append((where, ref))
            return
        if ref.startswith("MAQS:"):
            if ref[5:] not in MAQS_VALID:
                bad.append((where, ref))
            return
        if ref in LOG_VALID:  # bare 1.2 shorthand
            return
        if ref.startswith("LOG-"):
            target = LOG_VALID.get(ref)
            node = _get_path(standard, target) if target else None
            if node is None:
                bad.append((where, ref))
            return
        if ref.startswith("SCHEMA:"):
            if not (ROOT / "schemas" / ref[7:]).exists():
                bad.append((where, ref))
            return
        bad.append((where, ref))  # unknown namespace

    manifest = json.loads(MANIFEST.read_text())
    for entry in manifest:
        for r in entry.get("rules", []):
            check_ref(r, entry.get("id", "?"))
    for path in (ROOT / "schemas" / "b_write_integrity.json",
                 ROOT / "schemas" / "c8_classes.json"):
        for c in json.loads(path.read_text()):
            for r in c.get("rules", []):
                check_ref(r, f"{path.name}:{c.get('id')}")
    return bad


def check_pin():
    """Read canon value at run time, compare with vector fixture. Returns (ok, detail)."""
    pin = PINS["invalid-005"]
    try:
        text = (ROOT / pin["canon_file"]).read_text()
    except OSError as e:
        return False, f"canon unreadable: {e}"
    m = re.search(pin["canon_pattern"], text)
    if not m:
        return False, "canon pattern not found -> RED (not skip)"
    canon_value = float(m.group(1))
    vector = json.loads((ROOT / pin["vector"]).read_text())
    fixture_value = float(_get_path(vector, pin["field"]))
    if fixture_value != canon_value:
        return False, f"canon-pin drift: fixture {fixture_value} != canon {canon_value}"
    return True, f"fixture {fixture_value} == canon {canon_value} ({pin['canon_file']})"


def collect_gaps():
    gaps = []
    b = json.loads((ROOT / "schemas" / "b_write_integrity.json").read_text())
    gaps += [{"id": c["id"], "owner": c.get("owner"), "closes_in": c.get("closes_in")}
             for c in b if c.get("known_gap")]
    c8 = json.loads((ROOT / "schemas" / "c8_classes.json").read_text())
    gaps += [{"id": c["id"], "owner": c.get("owner"), "closes_in": c.get("closes_in")}
             for c in c8 if c.get("known_gap")]
    return gaps


def run_all(quiet=False):
    """Returns dict report; prints text unless format=json requested later."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf) if quiet else contextlib.nullcontext():
        schema_ok, schema_total = check_conformance.check_schema()
        manifest_ok, manifest_total, declared_ok, manifest_red = check_conformance.check_manifest()
        b_rc = check_b_coverage.main()
        c8_rc = check_c8_coverage.main()
        sb_ok, sb_total = check_scoreboard.check()
    manifest = json.loads(MANIFEST.read_text())
    declared_total = sum(1 for e in manifest if e.get("status") == "declared")
    ns_bad = check_namespaces()
    pin_ok, pin_detail = check_pin()
    rep_ok, rep_total, rep_err, rep_details = replay_vectors.run_all()
    gaps = collect_gaps()
    green = (schema_ok == schema_total and not manifest_red
             and not ns_bad and pin_ok and b_rc == 0 and c8_rc == 0
             and rep_err == 0 and rep_total > 0 and rep_ok == rep_total
             and sb_ok == sb_total and sb_total > 0)
    vector_status = {}
    for e in manifest:
        st = "declared" if e.get("status") == "declared" else "schema"
        vector_status[e["id"]] = st
    vector_status["invalid-005-shared-fact-visibility-leak"] = (
        "declared+pin-executed" if pin_ok else "declared+pin-RED"
    )
    return {
        "schema": {"passed": schema_ok, "total": schema_total},
        "manifest": {"passed": manifest_ok, "total": manifest_total},
        "behavioral": {"status": "declared", "passed": declared_ok, "total": declared_total},
        "executed": {"canon-pin": {"passed": 1 if pin_ok else 0, "total": 1,
                                   "detail": pin_detail},
                     "vectors": {"passed": rep_ok, "total": rep_total,
                                 "errors": rep_err, "detail": rep_details}},
        "scoreboard": {"passed": sb_ok, "total": sb_total},
        "namespaces": "ok" if not ns_bad else f"RED: {ns_bad}",
        "coverage": {"b_gate": "green-with-gap" if b_rc == 0 else "RED",
                     "c8_gate": "green-with-gap" if c8_rc == 0 else "RED",
                     "gaps": gaps},
        "vector_status": vector_status,
        "verdict": "GATE GREEN" if green else "GATE RED",
        "_green": green,
    }


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="MAQS-Way audit CLI v0.1")
    ap.add_argument("command", nargs="?", default="all",
                    choices=["schema", "manifest", "lint", "coverage", "all",
                             "namespaces", "pin", "replay", "scoreboard"])
    ap.add_argument("--format", default="text", choices=["text", "json"])
    args = ap.parse_args(argv)

    if args.command == "schema":
        ok, total = check_conformance.check_schema()
        rc = 0 if ok == total else 1
        if args.format == "json":
            print(json.dumps({"schema": {"passed": ok, "total": total},
                              "verdict": "GATE GREEN" if rc == 0 else "GATE RED"}))
        return rc
    if args.command == "manifest":
        ok, total, _, red = check_conformance.check_manifest()
        rc = 0 if (ok == total and not red) else 1
        if args.format == "json":
            print(json.dumps({"manifest": {"passed": ok, "total": total},
                              "verdict": "GATE GREEN" if rc == 0 else "GATE RED"}))
        return rc
    if args.command == "lint":
        _, _, dok, red = check_conformance.check_manifest()
        manifest = json.loads(MANIFEST.read_text())
        dtotal = sum(1 for e in manifest if e.get("status") == "declared")
        rc = 0 if (dok == dtotal and not red) else 1
        if args.format == "json":
            print(json.dumps({"behavioral": {"status": "declared",
                                             "passed": dok, "total": dtotal},
                              "verdict": "GATE GREEN" if rc == 0 else "GATE RED"}))
        else:
            print(f"behavioral-declared {dok}/{dtotal} (executable harness → package 1.4+)")
        return rc
    if args.command == "coverage":
        b_rc = check_b_coverage.main()
        c8_rc = check_c8_coverage.main()
        gaps = collect_gaps()
        for g in gaps:
            print(f"GAP: {g['id']} -> owner {g['owner']}, closes in {g['closes_in']}")
        rc = 0 if (b_rc == 0 and c8_rc == 0) else 1
        if args.format == "json":
            print(json.dumps({"coverage": {"b_gate": b_rc, "c8_gate": c8_rc,
                                           "gaps": gaps},
                              "verdict": "GATE GREEN" if rc == 0 else "GATE RED"}))
        return rc
    if args.command == "namespaces":
        bad = check_namespaces()
        if args.format == "json":
            print(json.dumps({"namespaces": "ok" if not bad else bad,
                              "verdict": "GATE GREEN" if not bad else "GATE RED"}))
        else:
            print("namespaces ok" if not bad else f"NAMESPACE RED: {bad}")
        return 0 if not bad else 1
    if args.command == "pin":
        ok, detail = check_pin()
        if args.format == "json":
            print(json.dumps({"executed": {"canon-pin": {"passed": 1 if ok else 0,
                                                         "total": 1, "detail": detail}},
                              "verdict": "GATE GREEN" if ok else "GATE RED"}))
        else:
            print(f"executed (canon-pin) {1 if ok else 0}/1: {detail}")
        return 0 if ok else 1
    if args.command == "replay":
        ok, total, err, details = replay_vectors.run_all()
        rc = 0 if (err == 0 and total > 0 and ok == total) else 1
        if args.format == "json":
            print(json.dumps({"executed": {"vectors": {"passed": ok, "total": total,
                                                        "errors": err, "detail": details}},
                              "verdict": "GATE GREEN" if rc == 0 else "GATE RED"}))
        else:
            for d in details:
                print(f"{d['state'].upper()} {d['id']}: {d['detail']}")
            print(f"replay-vectors {ok}/{total} (errors {err})")
        return rc
    if args.command == "scoreboard":
        ok, total = check_scoreboard.check()
        rc = 0 if (ok == total and total > 0) else 1
        if args.format == "json":
            print(json.dumps({"scoreboard": {"passed": ok, "total": total},
                              "verdict": "GATE GREEN" if rc == 0 else "GATE RED"}))
        return rc
    # all
    rep = run_all(quiet=(args.format == "json"))
    green = rep.pop("_green")
    if args.format == "json":
        print(json.dumps(rep, ensure_ascii=False, indent=2))
    else:
        s, m, b, x = rep["schema"], rep["manifest"], rep["behavioral"], rep["executed"]
        print(f"schema {s['passed']}/{s['total']} + manifest {m['passed']}/{m['total']} "
              f"+ declared {b['passed']}/{b['total']} "
              f"+ executed (canon-pin) {x['canon-pin']['passed']}/{x['canon-pin']['total']} "
              f"+ replay-vectors {x['vectors']['passed']}/{x['vectors']['total']} "
              f"+ scoreboard {rep['scoreboard']['passed']}/{rep['scoreboard']['total']} "
              f"+ namespaces {rep['namespaces']}")
        for g in rep["coverage"]["gaps"]:
            print(f"GAP (enumerated, not folded): {g['id']} -> owner {g['owner']}, "
                  f"closes in {g['closes_in']}")
        print(rep["verdict"])
    return 0 if green else 1


if __name__ == "__main__":
    sys.exit(main())
