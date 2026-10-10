"""Conformance gate for schemas/memory-item.schema.json (Way v0.1.3, SPEC §2.1).

Expected behavior (acceptance criteria of the schemas package):
- valid/001, valid/002 MUST validate (full §2.1 canon records).
- invalid/001 MUST FAIL (missing OAMP §4.3 binding + required fields).
- invalid/002 is expected to PASS structurally: its defect is semantic
  (model_output typed as trusted, MAQS F7) — caught by policy layer, not schema.
- valid/003 is a governance tombstone (separate artifact per §2.1), out of scope.

Run: python3 schemas/check_conformance.py
Exit 0 = gate green, non-zero = red.
"""
import json
import sys
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parent.parent
SCHEMA = ROOT / "schemas" / "memory-item.schema.json"

CASES = [
    ("conformance/valid/001-minimal-preference.omps.json", True),
    ("conformance/valid/002-bitemporal-fact.json", True),
    ("conformance/invalid/001-no-agent-id.json", False),
]


def main() -> int:
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    failed = False
    for rel, must_pass in CASES:
        doc = json.loads((ROOT / rel).read_text())
        errors = list(validator.iter_errors(doc))
        ok = not errors
        verdict = "PASS" if ok else "FAIL"
        expected = "PASS" if must_pass else "FAIL"
        mark = "OK " if verdict == expected else "GATE-RED"
        if verdict != expected:
            failed = True
        print(f"[{mark}] {rel}: got {verdict}, expected {expected}")
        for e in errors[:3]:
            print(f"       - {e.json_path}: {e.message}")
    print("GATE GREEN" if not failed else "GATE RED")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
