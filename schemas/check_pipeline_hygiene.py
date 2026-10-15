"""0.5a/0.6a pipeline-hygiene gate (Way package 1.7b).

Formulation lives in proposals/pipeline-hygiene-05a-06a.md (NOT canon).
0.5a/0.6a are known gaps (owner: 1.7b-formulation, closes_in: v0.2 canonization).

0.5a (self-hosting): every schemas/check_*.py is either invoked from
maqs_way_audit.py or listed in DECLARED_STANDALONE with a documented
integration point (the point document must mention "integration").
Uninvoked AND undocumented = dead -> RED. Closed list: extension by
package, never silently.
0.6a: current counters vs schemas/baseline.json within declared tolerance
(±10%) -> FLAG lines (advisory, exit 0). RED only for: baseline
missing/corrupt, or counter removed from tracking without explanation.

CLI integration point (documented, not implemented): `audit hygiene`
after v0.2 canonization. CLI 1.4 and gates 1.1–1.7a untouched.

Run: python3 schemas/check_pipeline_hygiene.py
Exit 0 = no hard failures (flags advisory), 1 = red.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "pipeline_hygiene.json"
BASELINE = ROOT / "schemas" / "baseline.json"
CLI = ROOT / "schemas" / "maqs_way_audit.py"

KNOWN_GAPS = {"0.5a", "0.6a"}

# Closed list: script -> document carrying its integration point.
DECLARED_STANDALONE = {
    "check_e_assembly.py": "proposals/e10-e11-assembly.md",
    "check_i13_redaction.py": "schemas/check_i13_redaction.py",
    "check_i_counters.py": "proposals/i10-i12-counters.md",
    "check_i_handlers.py": "proposals/i14-handlers.md",
    "check_i_layers.py": "proposals/i15-layers.md",
    "check_audit_procedure.py": "proposals/p9-p10-audit.md",
    "check_pipeline_hygiene.py": "proposals/pipeline-hygiene-05a-06a.md",
}


def current_counters():
    import json as _j
    return {
        "schemas.check_scripts": len(list((ROOT / "schemas").glob("check_*.py"))),
        "schemas.schema_json": len(list((ROOT / "schemas").glob("*.json"))),
        "conformance.vectors_valid": len(list((ROOT / "conformance" / "valid").glob("*.json"))),
        "conformance.vectors_invalid": len(list((ROOT / "conformance" / "invalid").glob("*.json"))),
        "conformance.manifest_entries": len(_j.loads((ROOT / "conformance" / "manifest.json").read_text())),
        "proposals.files": len(list((ROOT / "proposals").glob("*.md"))),
    }


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
            print(f"UNCOVERED (no owner): {c['id']}")
            print("GATE RED")
            return 1
    return 0


def check_dead_code():
    """0.5a self-hosting: wired or declared-with-point, else dead -> RED."""
    cli_src = CLI.read_text()
    wired = set(re.findall(r"import\s+(check_\w+)", cli_src))
    red = False
    for script in sorted((ROOT / "schemas").glob("check_*.py")):
        name = script.name
        mod = name[:-3]
        if mod in wired or f"from {mod} import" in cli_src:
            continue
        point_doc = DECLARED_STANDALONE.get(name)
        if point_doc is None:
            print(f"GATE RED — dead code (uninvoked, undeclared): {name}")
            red = True
            continue
        doc = (ROOT / point_doc).read_text()
        if "integration" not in doc.lower():
            print(f"GATE RED — declared point without integration doc: {name}")
            red = True
            continue
        print(f"declared-standalone (point ok): {name} -> {point_doc}")
    return 1 if red else 0


def check_baseline():
    """0.6a: drift -> FLAG (exit 0); missing/corrupt/removed -> RED (exit 1)."""
    try:
        base = json.loads(BASELINE.read_text())
    except (OSError, json.JSONDecodeError) as e:
        print(f"GATE RED — baseline missing/corrupt: {e}")
        return 1
    recorded = base.get("counters", {})
    tolerance = base.get("tolerance", 0.10)
    current = current_counters()
    removed = set(recorded) - set(current)
    if removed:
        print(f"GATE RED — counters removed from tracking unexplained: {sorted(removed)}")
        return 1
    for key, now in current.items():
        was = recorded.get(key)
        if was is None:
            print(f"FLAG (new counter, record it): {key} = {now}")
            continue
        drift = (now - was) / was if was else (1.0 if now else 0.0)
        if abs(drift) > tolerance:
            print(f"FLAG (drift {drift:+.0%} beyond ±{tolerance:.0%}): {key} {was} -> {now}")
    print(f"baseline provenance: {base.get('provenance', {})}")
    return 0


def main() -> int:
    if check_fixture() != 0:
        return 1
    rc = check_dead_code()
    if check_baseline() != 0:
        return 1
    if rc != 0:
        print("GATE RED")
        return 1
    print("COVERED 0/2 + KNOWN GAPS 2/2 (0.5a, 0.6a — formulation, canonization v0.2)")
    print("SELF-HOSTING ok (wired or declared-with-point); drift = flag, not verdict")
    print("GATE GREEN with known gap(s) — see owners above")
    return 0


if __name__ == "__main__":
    sys.exit(main())
