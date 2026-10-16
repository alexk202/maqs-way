"""Scoreboard gate: conformance/scoreboard.json must be honest and resolvable.

Checks (all local, no network):
- shape: every row has all columns, verdict in enum, executed is bool.
- NOT_AUDITED rows must carry a scope note in evidence (no silent blanks).
- every row has sha + audited date (provenance, no floating claims).
- no exact-duplicate rows (append-only discipline: new audit = new row).
- local SHA-resolve: docs/audits/<system>-way-audit.md exists and mentions
  the row's sha (falsifiability without network; remote resolve waits for
  scratch-runner).

Run: python3 schemas/check_scoreboard.py
Exit 0 = green, non-zero = red.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BOARD = ROOT / "conformance" / "scoreboard.json"

VERDICTS = {"COVERED", "PARTIAL", "GAP", "NOT_AUDITED"}
COLUMNS = ["system", "repo", "sha", "audited", "principle", "verdict",
           "executed", "one_line", "evidence"]

AUDIT_DOC = {"Mem0": "mem0-way-audit.md", "Graphiti": "graphiti-way-audit.md",
             "Letta": "letta-way-audit.md"}


def check() -> tuple[int, int]:
    board = json.loads(BOARD.read_text())
    rows = board.get("rows", [])
    ok, total = 0, 0
    seen = set()
    for r in rows:
        total += 1
        rid = f"{r.get('system')}/{r.get('principle')}"
        if sorted(r.keys()) != sorted(COLUMNS):
            print(f"GATE-RED {rid}: bad columns {sorted(r.keys())}")
            continue
        if r.get("verdict") not in VERDICTS:
            print(f"GATE-RED {rid}: bad verdict {r.get('verdict')!r}")
            continue
        if not isinstance(r.get("executed"), bool):
            print(f"GATE-RED {rid}: executed must be bool")
            continue
        if not r.get("sha") or not r.get("audited"):
            print(f"GATE-RED {rid}: sha+date required")
            continue
        if r["verdict"] == "NOT_AUDITED" and "scope" not in (r.get("evidence") or "").lower() and "not examined" not in (r.get("evidence") or "").lower() and "not covered" not in (r.get("evidence") or "").lower():
            print(f"GATE-RED {rid}: NOT_AUDITED needs a scope note")
            continue
        if not (r.get("evidence") or "").strip():
            print(f"GATE-RED {rid}: empty evidence")
            continue
        key = (r.get("system"), r.get("principle"), r.get("verdict"),
               r.get("sha"), r.get("evidence"))
        if key in seen:
            print(f"GATE-RED {rid}: exact-duplicate row (append-only violated)")
            continue
        seen.add(key)
        doc = AUDIT_DOC.get(r.get("system", ""))
        doc_path = ROOT / "docs" / "audits" / (doc or "")
        if not doc or not doc_path.exists() or r["sha"] not in doc_path.read_text():
            print(f"GATE-RED {rid}: sha {r.get('sha')} not resolved locally in {doc}")
            continue
        ok += 1
    cov = sum(1 for r in rows if r.get("verdict") == "COVERED")
    print(f"scoreboard {ok}/{total} rows valid ({cov} COVERED, all executed:false until WP2)")
    return ok, total


def main() -> int:
    ok, total = check()
    if ok != total:
        print("SCOREBOARD RED")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
