"""Conformance gate: schemas + manifest 12 + behavioral-declared (Way package 1.3).

Executable checks:
- schema 4/4: valid/001 + valid/002 + invalid/001 against
  schemas/memory-item.schema.json; valid/003 (governance tombstone) against
  schemas/deletion-marker.schema.json (new in 1.3).
  invalid/002 passes structurally by design (semantic defect: model_output typed
  as trusted, MAQS F7) — caught by policy layer, not schema.
- manifest 12/12: every manifest entry <-> file on disk, no orphans either way;
  entry shape strict (unknown marker keys like known_*/fixture_*/gap* -> BYPASS RED).
- behavioral-declared: vectors with status "declared" are scenario fixtures, NOT
  semantically executed here — structural lint only (doc has scenario or id;
  entry declares expected + rules). Executable harness lands in package 1.4.

Mixed rule style (P4+G1, P1+P3+F) is canonical per v0.1.3 precedent;
namespacing normalization (Way:/MAQS:/LOG:) is a separate package, post-1.4.

Run: python3 schemas/check_conformance.py
Exit 0 = gate green, non-zero = red.
"""
import json
import sys
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA_ITEM = ROOT / "schemas" / "memory-item.schema.json"
SCHEMA_MARKER = ROOT / "schemas" / "deletion-marker.schema.json"
MANIFEST = ROOT / "conformance" / "manifest.json"

# (relative path, schema file, must_pass)
SCHEMA_CASES = [
    ("conformance/valid/001-minimal-preference.omps.json", SCHEMA_ITEM, True),
    ("conformance/valid/002-bitemporal-fact.json", SCHEMA_ITEM, True),
    ("conformance/invalid/001-no-agent-id.json", SCHEMA_ITEM, False),
    ("conformance/valid/003-deletion-tombstone.json", SCHEMA_MARKER, True),
]

ENTRY_KEYS = {"id", "file", "expected", "status", "rules", "reason"}
STATUS_VALUES = {"declared"}


def check_schema() -> tuple[int, int]:
    ok_count, total = 0, 0
    failed = False
    for rel, schema_path, must_pass in SCHEMA_CASES:
        total += 1
        schema = json.loads(schema_path.read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        doc = json.loads((ROOT / rel).read_text())
        errors = list(validator.iter_errors(doc))
        ok = not errors
        verdict = "PASS" if ok else "FAIL"
        expected = "PASS" if must_pass else "FAIL"
        mark = "OK " if verdict == expected else "GATE-RED"
        if verdict != expected:
            failed = True
        else:
            ok_count += 1
        print(f"[{mark}] {rel}: got {verdict}, expected {expected}")
        for e in errors[:3]:
            print(f"       - {e.json_path}: {e.message}")
    if failed:
        print("SCHEMA RED")
    return ok_count, total


def check_manifest() -> tuple[int, int, int, bool]:
    """Returns (manifest_ok, manifest_total, declared_ok, red)."""
    manifest = json.loads(MANIFEST.read_text())
    red = False
    manifest_ok = 0
    declared_ok = 0
    seen_files = set()
    for entry in manifest:
        eid = entry.get("id", "<no-id>")
        keys = set(entry.keys())
        unknown = keys - ENTRY_KEYS
        if unknown:
            marker = [k for k in unknown if k.startswith(("known_", "fixture_", "gap"))]
            if marker:
                print(f"BYPASS ATTEMPT in {eid}: marker keys {sorted(marker)}")
            else:
                print(f"GATE-RED {eid}: unknown entry keys {sorted(unknown)}")
            red = True
            continue
        rel = entry.get("file", "")
        if not rel or (ROOT / "conformance" / rel) in seen_files or not (ROOT / "conformance" / rel).exists():
            print(f"GATE-RED {eid}: file missing or duplicated: {rel}")
            red = True
            continue
        seen_files.add(ROOT / "conformance" / rel)
        if entry.get("expected") not in ("PASS", "FAIL"):
            print(f"GATE-RED {eid}: broken expected verdict: {entry.get('expected')!r}")
            red = True
            continue
        if not entry.get("rules"):
            print(f"GATE-RED {eid}: no rules declared")
            red = True
            continue
        status = entry.get("status")
        if status is not None and status not in STATUS_VALUES:
            print(f"GATE-RED {eid}: unknown status {status!r}")
            red = True
            continue
        manifest_ok += 1
        if status == "declared":
            doc = json.loads((ROOT / "conformance" / rel).read_text())
            if not isinstance(doc, dict) or ("scenario" not in doc and "id" not in doc):
                print(f"GATE-RED {eid}: declared vector has no scenario/id")
                red = True
                continue
            declared_ok += 1
    # Orphan check: every vector file on disk must be listed.
    on_disk = set((ROOT / "conformance" / "valid").glob("*.json")) | set(
        (ROOT / "conformance" / "invalid").glob("*.json")
    )
    orphans = on_disk - seen_files
    for o in sorted(orphans):
        print(f"GATE-RED orphan vector (no manifest entry): {o.relative_to(ROOT)}")
        red = True
    return manifest_ok, len(manifest), declared_ok, red


def main() -> int:
    schema_ok, schema_total = check_schema()
    manifest_ok, manifest_total, declared_ok, manifest_red = check_manifest()
    declared_total = sum(
        1 for e in json.loads(MANIFEST.read_text()) if e.get("status") == "declared"
    )
    print(
        f"schema {schema_ok}/{schema_total} + manifest {manifest_ok}/{manifest_total} "
        f"+ behavioral-declared {declared_ok}/{declared_total} "
        f"(executable harness → package 1.4) → "
        f"{'GATE RED' if (schema_ok != schema_total or manifest_red) else 'GATE GREEN'}"
    )
    if schema_ok != schema_total or manifest_red:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
