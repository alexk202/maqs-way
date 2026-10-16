"""Executable replay for declared vectors (v0.3 WP1, standalone module).

Audit (`maqs_way_audit.py`) checks canon conformance; this module checks that
the checking machinery works: each declared vector is replayed and must
reproduce its predicted outcome. Audit and self-test stay separate bodies
(prec. 1.6b-1.6d standalone gates, promotion `negative-red/replay_red.py`).

Honest scope: replays assert FIXTURE SEMANTICS + gate agreement (the trap is
shaped correctly, the owner rule is labeled, the canon number matches).
Live-system behavior (real tenants, stores, model runs) remains backlog —
see SPEC §6. A replay that proves the fixture is honest is not a proof that
a product passes; it is a proof that the detector can fire.

Three states per vector, never merged:
- caught: predicted outcome reproduced (expected RED structure confirmed).
- missed: replay disagrees with the manifest (canon bug) -> gate RED.
- error: replay could not run (missing file, bad shape) -> gate RED as
  environment failure, distinct from verdict (never silent green).

Usage: python3 schemas/replay_vectors.py  (exit 0 iff all caught, no errors)
"""

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "conformance" / "manifest.json"
CONF = ROOT / "conformance"
SPEC = ROOT / "SPEC.md"


def _entry_doc(entry):
    return json.loads((CONF / entry["file"]).read_text())


def _has_rules(entry, *want):
    rules = entry.get("rules", [])
    return all(w in rules for w in want)


def replay_002(entry):
    """Schema trap: model output stored as trusted (must be schema-PASS,
    policy-owned)."""
    d = _entry_doc(entry)
    src = d["provenance"]["source"]
    ok = (src["type"] == "model_output"
          and d["provenance"]["confidence"] == 1.0
          and "confidence_after" not in d["provenance"]
          and entry.get("expected") == "FAIL"
          and _has_rules(entry, "Way:P1", "MAQS:F7"))
    return ok, "model_output@1.0 trusted, no ceiling, owned by P1/F7"


def replay_003(entry):
    """Cross-tenant breach shape: B reads A's memory."""
    d = _entry_doc(entry)
    ok = (d["query_user"] != d["returned_memory"]["subject"]["id"]
          and entry.get("expected") == "FAIL"
          and _has_rules(entry, "Way:P4", "MAQS:G"))
    return ok, f"{d['query_user']} read {d['returned_memory']['subject']['id']}, owned by P4/G"


def replay_004(entry):
    """Native delete leaves residue (bench: ~100% recoverable)."""
    d = _entry_doc(entry)
    ok = (float(d["recoverable_percent"]) >= 90.0
          and entry.get("expected") == "FAIL"
          and _has_rules(entry, "Way:P5"))
    return ok, f"residue {d['recoverable_percent']}% without compaction, owned by P5"


def replay_005(entry):
    """Shared-fact pin: fixture threshold == canon SPEC §3.3 at runtime."""
    d = _entry_doc(entry)
    m = re.search(r"SEMANTIC:\s*embedding similarity\s*<\s*(\d+(?:\.\d+)?)",
                  SPEC.read_text())
    if not m:
        raise RuntimeError("canon pattern missing in SPEC.md")
    canon = float(m.group(1))
    fx = float(d["fixture"]["similarity_threshold"])
    ok = (fx == canon
          and entry.get("expected") == "FAIL"
          and _has_rules(entry, "Way:P4", "MAQS:G1"))
    return ok, f"fixture {fx} == canon {canon}"


def replay_006(entry):
    """G1 wrong-scope: claimed scope != actual scope must BLOCK."""
    d = _entry_doc(entry)
    q = d["query"]
    ok = (q["scope_claimed"] != q["actual_memory_scope"]
          and "BLOCK" in d.get("otel_expected", "")
          and entry.get("expected", "").startswith("FAIL")
          and _has_rules(entry, "Way:P4", "MAQS:G1"))
    return ok, f"{q['scope_claimed']} vs {q['actual_memory_scope']}, BLOCK expected"


def replay_007(entry):
    """G1 readonly: temporary session write must BLOCK."""
    d = _entry_doc(entry)
    ok = ("write_attempt" in d.get("session", {})
          and "BLOCK" in d.get("expected", "")
          and entry.get("expected") == "FAIL"
          and _has_rules(entry, "Way:P4"))
    return ok, "ephemeral write_attempt must BLOCK, owned by P4"


def replay_008(entry):
    """G1 revocation: grant -> revoke -> search must yield nothing."""
    d = _entry_doc(entry)
    steps = [s.lower() for s in d.get("steps", [])]
    ok = (len(steps) >= 3 and steps[0].startswith("grant")
          and "revoke" in steps[1] and "search" in steps[2]
          and "residue 0" in d.get("expected", "")
          and entry.get("expected") == "FAIL"
          and _has_rules(entry, "Way:P4", "Way:P5"))
    return ok, "grant->revoke->search, LOGICAL residue 0"


def replay_009(entry):
    """Stale summary escalates trust (0.6->0.9): F8 violation shape."""
    d = _entry_doc(entry)
    s = d["setup"]["stale_summary"]
    ok = (s["type"] == "model_output"
          and float(s["confidence_after"]) > float(s["confidence_before"])
          and "confidence_after <= confidence_before" in d.get("expected", "")
          and entry.get("expected") == "FAIL"
          and _has_rules(entry, "Way:P1", "Way:P3", "MAQS:F"))
    return ok, f"escalation {s['confidence_before']}->{s['confidence_after']}, owned by P1/P3/F"


REPLAYS = {
    "invalid-002-model-output-as-trusted": replay_002,
    "invalid-003-cross-tenant": replay_003,
    "invalid-004-native-delete-residue": replay_004,
    "invalid-005-shared-fact-visibility-leak": replay_005,
    "invalid-006-wrong-scope-leak": replay_006,
    "invalid-007-readonly-write-block": replay_007,
    "invalid-008-revoked-access-leak": replay_008,
    "invalid-009-stale-overrides-fresh": replay_009,
}


def run_all():
    """Returns (passed, total, errors, details). Never prints."""
    manifest = json.loads(MANIFEST.read_text())
    passed, errors, details = 0, 0, []
    total = 0
    for entry in manifest:
        fn = REPLAYS.get(entry.get("id", ""))
        if fn is None:
            continue
        total += 1
        try:
            caught, detail = fn(entry)
        except Exception as e:  # noqa: BLE001 — error is a state, not a crash
            errors += 1
            details.append({"id": entry["id"], "state": "error",
                            "detail": f"{type(e).__name__}: {e}"})
            continue
        if caught:
            passed += 1
            details.append({"id": entry["id"], "state": "caught", "detail": detail})
        else:
            details.append({"id": entry["id"], "state": "missed", "detail": detail})
    return passed, total, errors, details


def main() -> int:
    passed, total, errors, details = run_all()
    for d in details:
        print(f"[{d['state'].upper()}] {d['id']}: {d['detail']}")
    if errors or passed != total:
        print(f"REPLAY RED: {passed}/{total} caught, {errors} errors")
        return 1
    print(f"REPLAY GREEN: {passed}/{total} caught, 0 errors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
