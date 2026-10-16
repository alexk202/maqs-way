"""WP2 calibration runner — SKELETON (no measurements yet).

Refuses to fake numbers: without datasets + pinned open-weights model it
reports NOT-RUN (exit 2, distinct from pass/fail) and lists exactly what is
missing. When inputs exist, it records env provenance per number and runs
the declared suite; thresholds are confronted with prereg-v03.md, never
silently retargeted.

Usage:
  python evals/run_way_evals.py --standard maqs-way-standard.json --out evals/results/<date>/
"""
import argparse
import json
import platform
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REQUIRED_DATASETS = ["locomo", "longmemeval"]


def env_provenance():
    return {
        "runner": platform.node(),
        "python": platform.python_version(),
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seeds": "NOT-SET",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description="WP2 calibration runner (skeleton)")
    ap.add_argument("--standard", default=str(ROOT / "maqs-way-standard.json"))
    ap.add_argument("--model", default=None, help="pinned open-weights model id")
    ap.add_argument("--datasets", default=str(ROOT / "evals" / "datasets"))
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    standard = json.loads(Path(args.standard).read_text())
    metrics = standard.get("verification_suite", {}).get("metrics", {})
    missing = []
    ds = Path(args.datasets)
    for name in REQUIRED_DATASETS:
        if not (ds / name).exists():
            missing.append(f"datasets/{name}")
    if not args.model:
        missing.append("--model (pinned open-weights id)")
    if missing:
        print("NOT-RUN (skeleton): missing inputs, no numbers produced:")
        for m in missing:
            print(f"  - {m}")
        print(f"metrics declared in standard: {sorted(metrics)}")
        print(f"env provenance that WILL accompany numbers: {env_provenance()}")
        print("see evals/prereg-v03.md for pre-registered expectations")
        return 2
    print("inputs present — measurement harness lands here (WP2 full)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
