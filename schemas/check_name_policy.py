"""Name-policy gate (owner rule 2026-10-24): no personal names in public repo
docs/code/commit messages except the project author. Wraps
.githooks/name_guard.py scan_all() -- the SAME pattern source as the
pre-commit/commit-msg hooks (single source of truth; the 2026-10-24 recurrence
happened exactly because scan and hook patterns had diverged). Skips mirror
the hook's: benchmark dataset (data, not leaks), results/ (run artifacts carry
benchmark entity names), .githooks/ (pattern carrier).

Run: python3 schemas/check_name_policy.py
Exit 0 = green, 1 = red.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".githooks"))

import name_guard  # noqa: E402


def main() -> int:
    hits = name_guard.scan_all()
    for f, lines in hits:
        print(f"GATE-RED name policy: {f} (lines {lines[:8]})")
    if hits:
        print(f"name policy: {len(hits)} file(s) with name leaks -- RED")
        return 1
    print("name policy: 0 leaks in tracked files -- GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
