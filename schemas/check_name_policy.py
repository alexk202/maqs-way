"""Name-policy gate (owner rule 2026-10-24): no personal names in public repo
docs/code/commit messages except the project author. Wraps
.githooks/name_guard.py scan_core(REPO_ROOT) -- the SAME pattern source as the
pre-commit/commit-msg hooks (single source of truth). Skips mirror the hook's:
benchmark dataset (data, not leaks), results/ (run artifacts carry benchmark
entity names), .githooks/ (pattern carrier).

Repo binding (external-audit finding, 2026-10-24): the scan targets THIS
repository (derived from the script's own path), not the caller's cwd; the
evidence-repo CI and GitHub Actions invoke this gate from foreign trees.
FAIL-CLOSED: git unavailable / not a repository / no tracked files -> RED.

Self-test (--selftest): (1) the scan result is identical when the CLI is
launched from the repo root, from a non-git temp dir, and from a foreign git
repo; (2) a non-repo root and a git-less PATH both yield the FAIL-CLOSED red,
never green.

Run: python3 schemas/check_name_policy.py [--selftest]
Exit 0 = green, 1 = red, 2 = selftest failed.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / ".githooks"))

import name_guard  # noqa: E402

FOREIGN_REPO = None  # resolved lazily by selftest


def scan() -> tuple[list, str | None]:
    return name_guard.scan_core(ROOT)


def main() -> int:
    if "--selftest" in sys.argv[1:]:
        return selftest()
    hits, err = scan()
    if err:
        print(f"GATE-RED name policy: scan failed -- {err}")
        print("name policy: FAIL-CLOSED (cannot scan -> red, never green)")
        return 1
    for f, lines in hits:
        print(f"GATE-RED name policy: {f} (lines {lines[:8]})")
    if hits:
        print(f"name policy: {len(hits)} file(s) with name leaks -- RED")
        return 1
    print("name policy: 0 leaks in tracked files -- GREEN "
          f"(bound to {ROOT.name}, any cwd)")
    return 0


def _run_cli(cwd):
    return subprocess.run([sys.executable, str(Path(__file__).resolve())],
                          capture_output=True, text=True, cwd=str(cwd))


def selftest() -> int:
    ok = True

    def check(name, cond, detail=""):
        nonlocal ok
        print(f"  {'PASS' if cond else 'FAIL'}  {name}" + (f" -- {detail}" if detail and not cond else ""))
        ok = ok and cond

    # 1) cwd-independence: identical verdict from repo root, non-git dir, foreign repo
    with tempfile.TemporaryDirectory() as non_git:
        foreign = Path.home() / "Projects" / "memory-architecture-standard"
        cwds = [ROOT, Path(non_git)] + ([foreign] if foreign.exists() else [])
        results = [(p.returncode, p.stdout.strip()) for p in map(_run_cli, cwds)]
        check("identical scan from all cwds",
              len({r for r in results}) == 1,
              f"results differ: {results}")
        check("verdict is green on the clean tree",
              results and results[0][0] == 0,
              f"rc={results[0][0] if results else '?'}")

    # 2) fail-closed: non-repo root
    with tempfile.TemporaryDirectory() as td:
        hits, err = name_guard.scan_core(Path(td))
        check("non-repo root -> error, not green", err is not None and hits is None)

    # 3) fail-closed: git unavailable
    env = dict(os.environ)
    env["PATH"] = "/nonexistent-for-selftest"
    p = subprocess.run([sys.executable, str(Path(__file__).resolve())],
                       capture_output=True, text=True, cwd="/tmp", env=env)
    check("git-less PATH -> RED (fail-closed), not GREEN",
          p.returncode == 1 and "FAIL-CLOSED" in p.stdout,
          f"rc={p.returncode}, out={p.stdout.strip()[:80]}")

    print("name-policy selftest:", "PASS" if ok else "FAIL")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main())
