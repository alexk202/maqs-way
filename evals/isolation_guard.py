"""MAQS H5 [CRIT] isolation guard — built into every eval runner, runs in
EVERY run (not periodically). Extends the H5 line from the MAQS [Unreleased]
notes: evals must never touch the live memory stores on this machine, and the
promise "guard check before/after live directories" (README "Isolation") is
enforced by code, not by convention.

WHAT IS GUARDED (live stores = anything outside the per-run temp store):
  1. ~/.mem0                 — mem0 default dir: history.db (SQLite), config.json,
                               migrations_qdrant/ locks and anything else inside;
  2. ~/.local/share/qdrant   — qdrant-client local default storage root;
  3. ~/.cache/qdrant         — qdrant-client cache root;
  plus EVAL_GUARD_PATHS       — colon-separated extra roots (foreign stands
                               can extend the guarded set without code edits).

Roots that do not exist are guarded as empty: anything created there during a
run is a leaked artifact and turns the guard RED.

HOW THE COMPARISON WORKS (before-snapshot -> run -> after-snapshot):
  - file SET: a file appearing under a guarded root that was not in the
    before-snapshot, or a snapshot file disappearing -> RED (leak);
  - file CONTENT:
      * SQLite databases (*.db, *.sqlite, *.sqlite3) are compared by LOGICAL
        ROWS (SELECT from every table), never by md5/bytes: a WAL checkpoint
        rewrites the main file bytes without any data change -- byte-hashing
        a live WAL base false-REDs (known checkpoint trap). Reads use
        immutable=1 URIs so the guard itself cannot touch the files;
      * every other file: sha256 of bytes;
  - SQLite side files (-wal, -shm, -journal) are ignored: transient by design
    (any process opening a WAL base flips them; the data rows carry the signal).

SEMANTICS OF RED: any divergence after the run body means the run touched a
live store. The @guarded() decorator prints the divergences and forces a
non-zero exit code (runners keep `sys.exit(main())`). The verify step runs
even when the run body raises.

HISTORY REDIRECT: runners must also pass "history_db_path" into their mem0
config via temp_history_db(<per-question store dir>) below. Without it mem0
v2.2.1 defaults to ~/.mem0/history.db and BOTH WRITES every ingested session
(SQLiteManager save_messages) and READS the last 10 messages of the same scope
(get_last_messages -> "## Last k Messages" section of the extraction prompt).
That bidirectional live-store contamination was discovered 2026-10-25 while
building this guard: every pilot since Oct 16-17 appended raw haystack content
to the live history db (7.4 MB / 22940 rows of extracted-fact events; the raw
messages themselves live under a 10-row-per-scope eviction cap) and fed an
uncontrolled tail of previous questions/runs into every extraction call.
GRANULARITY (owner decision 2026-10-25, after the g1-iso-a STOP): the redirect
is PER QUESTION — temp_history_db(f"{STORE}/q{qi}") — so get_last_messages is
empty for every extraction call. An earlier per-RUN variant (one history.db
shared by all questions of a run) moved the channel off the live store but
KEPT the within-run sliding tail; the g1-iso-a run exposed it (same 16.5%
foreign-fact rate as frozen g1; see results/g1iso_a_note.md) and it was
superseded within the same day. The guard itself is unchanged by granularity.

Known limitation (honest): if a NON-eval process legitimately writes a live
store while a run is in progress, the guard fires RED. On a machine where the
eval process is the only mem0 consumer this is the intended semantics; the
divergence report names the paths so a human can adjudicate.
"""
import functools
import hashlib
import os
import sqlite3
import sys
from pathlib import Path

SQLITE_SUFFIXES = (".db", ".sqlite", ".sqlite3")
SQLITE_SIDECARS = ("-wal", "-shm", "-journal")

TAG = "[H5 isolation guard]"


def guarded_roots():
    """Live-store roots under guard (default set + EVAL_GUARD_PATHS extras)."""
    home = Path.home()
    roots = [
        home / ".mem0",
        home / ".local" / "share" / "qdrant",
        home / ".cache" / "qdrant",
    ]
    for extra in os.environ.get("EVAL_GUARD_PATHS", "").split(":"):
        if extra.strip():
            roots.append(Path(extra.strip()).expanduser())
    seen, uniq = set(), []
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            uniq.append(r)
    return uniq


def _sqlite_fingerprint(path):
    """Logical-row fingerprint of a SQLite file (checkpoint-safe)."""
    con = sqlite3.connect(f"file:{path}?mode=ro&immutable=1", uri=True)
    try:
        payload = []
        tables = [r[0] for r in con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
        for t in tables:
            rows = con.execute(f'SELECT * FROM "{t}"').fetchall()
            payload.append((t, len(rows), rows))
        return "sqlite:" + hashlib.sha256(repr(payload).encode()).hexdigest()
    finally:
        con.close()


def _byte_fingerprint(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _fingerprint(path):
    try:
        if path.name.endswith(SQLITE_SUFFIXES) or path.suffix in SQLITE_SUFFIXES:
            try:
                return _sqlite_fingerprint(path)
            except Exception:
                pass  # named like a db but not one -> fall through to bytes
        return _byte_fingerprint(path)
    except OSError:
        return "unreadable"


def snapshot():
    """Full state of all guarded roots: {root: {relpath: fingerprint}}."""
    snap = {}
    for root in guarded_roots():
        files = {}
        if root.is_dir():
            for p in sorted(root.rglob("*")):
                if p.is_file() and not p.name.endswith(SQLITE_SIDECARS):
                    files[str(p.relative_to(root))] = _fingerprint(p)
        snap[str(root)] = files
    return snap


def verify(snap):
    """Divergences between a before-snapshot and the current state."""
    fails = []
    for root_s, before in snap.items():
        root = Path(root_s)
        after = {}
        if root.is_dir():
            for p in sorted(root.rglob("*")):
                if p.is_file() and not p.name.endswith(SQLITE_SIDECARS):
                    after[str(p.relative_to(root))] = _fingerprint(p)
        for rel in sorted(set(before) - set(after)):
            fails.append(f"{root_s}: guarded file DISAPPEARED: {rel}")
        for rel in sorted(set(after) - set(before)):
            fails.append(f"{root_s}: NEW artifact leaked: {rel}")
        for rel in sorted(set(before) & set(after)):
            if before[rel] != after[rel]:
                kind = "sqlite rows changed" if before[rel].startswith("sqlite:") \
                    else "file content changed"
                fails.append(f"{root_s}: {kind}: {rel}")
    return fails


def temp_history_db(store):
    """history_db_path for a runner's mem0 config: callers pass the
    PER-QUESTION store dir (e.g. f"{STORE}/q{qi}") so every extraction call
    sees an empty get_last_messages; mkdir parents so sqlite3.connect never
    fails on a fresh store. See the H5 note in the module docstring: mem0
    v2.2.1 otherwise defaults to the live ~/.mem0/history.db and both reads
    and writes it during add()."""
    p = Path(store) / "history.db"
    p.parent.mkdir(parents=True, exist_ok=True)
    return str(p)


# Snapshot taken at THIS module's import time. Runners import the guard
# before `from mem0 import Memory`, so the earliest observable state wins:
# import-time side effects of the SUT stack are inside the guarded window.
_IMPORT_SNAPSHOT = snapshot()


def guarded(_func=None, *, label=None):
    """Decorator for a runner's main(): snapshot (at guard-import time, see
    above) -> run body -> verify. Divergence => RED lines + exit code 1.
    Verify runs even if the body raises."""
    def deco(fn):
        @functools.wraps(fn)
        def wrapper(*a, **kw):
            tag = label or f"{fn.__module__}.{fn.__name__}"
            snap = _IMPORT_SNAPSHOT
            n_files = sum(len(v) for v in snap.values())
            print(f"{TAG} snapshot: {len(snap)} roots, {n_files} files "
                  f"(before {tag})", flush=True)
            try:
                rc = fn(*a, **kw)
            finally:
                fails = verify(snap)
                if fails:
                    print(f"{TAG} RED — live stores diverged after {tag}:",
                          flush=True)
                    for f in fails:
                        print(f"{TAG} RED: {f}", flush=True)
                    print(f"{TAG} RED: isolation H5 violated — treat all "
                          f"artifacts of this run as contaminated.", flush=True)
                else:
                    print(f"{TAG} GREEN — live stores untouched.", flush=True)
            return 1 if fails else (rc if isinstance(rc, int) else 0)
        return wrapper
    if _func is not None:  # used as @guarded without parentheses
        return deco(_func)
    return deco


def _selftest():
    """Negative self-test without a stand: snapshot -> synthetic write into a
    guarded root -> must RED; cleanup -> must GREEN again. Exits 0 iff both
    hold. Run: python3 isolation_guard.py selftest"""
    probe = Path.home() / ".mem0" / "_guard_selftest_probe.tmp"
    snap = snapshot()
    probe.write_text("leak probe")
    fails = verify(snap)
    probe.unlink()
    fails_clean = verify(snap)
    ok = bool(fails) and not fails_clean
    print(f"selftest: leak detected: {bool(fails)} ({fails}); "
          f"clean pass: {not fails_clean} -> {'OK' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "selftest":
        sys.exit(_selftest())
    print(f"{TAG} guarded roots:")
    for r in guarded_roots():
        n = sum(1 for _ in r.rglob("*")) if r.is_dir() else 0
        print(f"  {r} {'(' + str(n) + ' entries)' if r.is_dir() else '(absent)'}")
    sys.exit(0)
