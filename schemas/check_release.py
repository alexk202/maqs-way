"""Release gate (Way package 1.8): G0/G3/G4/G5/G6/G7/G8 executable.

TARGET-PARAMETERIZED (v0.2.1 release): the expected release stamp is passed
with --target (default: the current release window, 0.2.1) instead of being
hard-coded per release. The previous stamp for the stale checks is derived
(patch-1 / minor-1) and overridable with --prev.

G0 canon integrity: H1/Status v{target} (EN/RU), JSON version {target},
  schema_version frozen (way-v0.1.3 present, no bump), `masked` absent
  from states/status_enum, previous release stamps only in §7 history.
G1/G2 (mirror + derivatives): MANUAL checklist boundary — stated, not
  pretended executable. See release report.
Manual release-sync items (owner, together with the release):
  - CITATION.cff: bump version + date-released to the release stamp
    (free commit, same release window; never silently between releases).
  - After the release is published: the new version's DOI from Zenodo goes
    into CITATION.cff (doi field) and into the README DOI badge — separate
    post-release commit; the release tag is never moved for it.
  - CITATION.cff validation (cffconvert) runs ONLY in an isolated
    environment — `pipx run cffconvert --validate` (or a temporary venv);
    never pip-install cffconvert into a project/dev environment (it
    silently downgraded jsonschema there and broke the gates' imports).
G3 verifiability: audit all GREEN + manifest count 12 + landscape file
  present with verified column (link liveness itself is owner-verified).
G4 process purity: §7 carries the v{prev}→v{target} entry WITH the
  open-gap list.
G5 honesty (added 1.8): no known gap list targets THIS release version
  without proven closure. Silence about gaps = false green.
G6 hygiene-all-green (v0.3 step 8, owner amendment): runs ALL
  schemas/check_*.py EXCEPT this script (no infinite self-run); each
  script runs WITHOUT arguments; criterion = exit code (0 = pass,
  including 'GREEN with advisory/known gap'; non-zero = RED); a script
  that requires arguments or crashes = RED with its name, no silent
  skips; the output lists every run script and its result -- a red gate
  can no longer slip into a release unnoticed.
G7 forward refs to released versions (owner task 2026-10-29): in
  SPEC.md and SPEC-RU.md outside §7, flags future-facing promises
  pinned to a version <= the release target ("TODO v0.N",
  "deferred to v0.N", "to be added in v0.N", "planned for v0.N",
  "planned in v0.N", "closes in v0.N"; RU: "TODO v0.N",
  "отложено до v0.N", "будет добавлено в v0.N",
  "запланировано на/в v0.N"; RU extensions (owner amendment,
  stale-refs application 2026-10-29): "перенесен/а/о в v0.N",
  "будет добавлен/а/о в v0.N", "отложен/а/о до v0.N") -- by the v0.4
  release a promise addressed to v0.2 points at an already-released
  version, i.e. a stale reference. Version comparison is numeric
  (v0.2 <= v0.4).
  Active from --target 0.4; for a lower target it prints a skip line
  and does not affect the verdict (the v0.3 verdict stays
  reproducible). Limitation: formulations WITHOUT the version marker
  ("Normative thresholds in v0.2") are NOT caught by G7 -- they are
  closed by the stale-refs inventory (docs/v0.4-canon/stale-refs.md),
  not by this gate.
G8 single source for the declared MAQS version (owner task 2026-11-11):
  the MAQS core version is declared ONCE, in maqs-way-standard.json
  `maqs_core_reference`; every mention in the tracked version-bearing
  files (G8_FILES: SPEC.md, SPEC-RU.md, maqs-way-standard.json,
  docs/mapping-to-maqs.md, README.md) must equal it. The canon version
  is extracted with `MAQS v?(\\d+\\.\\d+(?:\\.\\d+)?)` from that value;
  a missing field or an unextractable version is GATE RED with an
  explicit message (never a silent skip).
  Exceptions (historical mentions), applied mechanically:
   1. the occurrence sits inside backticks (a file name or path);
   2. it is part of a sync phrase -- followed by the word `sync`
      ("MAQS 1.8.1 sync") or, in the RU mirror, preceded by it
      ("Из синхронизации MAQS 1.8.1");
   3. it sits in the §7 Change Log (split on "## 7.", as G0/G7 do).
  Standalone version tokens only: item ids such as "MAQS 0.5a" are not
  version mentions (no lookahead match past a letter).
  Active for ANY --target (unlike G7): it checks tree consistency, not
  release readiness. Not reachable from G6 (check_release.py is
  self-excluded there). Self-check of the three RED/GREEN shapes on
  temp copies outside the repo: `--self-test` (mechanics as in the
  evidence repo's negative-red/replay_red.py).

Integration point: manual release gate (G0-G5/G6), invoked by the
release procedure; deliberately NOT wired into maqs_way_audit all
(release-only). Declared standalone (0.5a, v0.3 step 8).

Run: python3 schemas/check_release.py [--target 0.3] [--prev 0.2.1]
Target forms: SPEC/§7/tag display form ("0.3" -> SPEC "v0.3", §7 "v0.2.1 →
v0.3"); the JSON stamp is the full three-part form (two-part targets get
".0" appended: 0.3 -> JSON 0.3.0) per the release version convention.
Exit 0 = releasable, 1 = red.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = "0.2.1"


def _json_stamp(target: str) -> str:
    """Target -> JSON version stamp per the release version convention:
    two-part targets are the display form (0.3 -> SPEC v0.3) and the JSON
    carries the full stamp (0.3.0); three-part targets pass through."""
    return target + ".0" if target.count(".") == 1 else target


def _prev_stamp(target: str) -> str:
    """Best-effort previous stamp: decrement patch, else minor
    (0.2.1 -> 0.2.0; 0.3.0 -> 0.2.0). Override with --prev when the
    release line is not patch-incrementing."""
    parts = target.split(".")
    if len(parts) == 3 and all(p.isdigit() for p in parts):
        x, y, z = (int(p) for p in parts)
        if z > 0:
            return f"{x}.{y}.{z - 1}"
        if y > 0:
            return f"{x}.{y - 1}.0"
    return target


def _display(stamp: str) -> str:
    """Stamp -> release display form: 0.2.0 -> v0.2, 0.2.1 -> v0.2.1."""
    return "v" + (stamp[:-2] if stamp.endswith(".0") else stamp)


def fail(msg):
    print(f"GATE RED — {msg}")
    return False


def check_g0(target, prev, prev_display):
    ok = True
    spec = (ROOT / "SPEC.md").read_text()
    ru = (ROOT / "SPEC-RU.md").read_text()
    if f"# MAQS-Way v{target} " not in spec or f"**Status:** v{target}" not in spec:
        ok = fail(f"G0 EN stamps (H1/Status v{target})")
    if f"# MAQS-Way v{target} " not in ru or f"**Статус:** v{target}" not in ru:
        ok = fail(f"G0 RU stamps (H1/Status v{target})")
    std = json.loads((ROOT / "maqs-way-standard.json").read_text())
    json_stamp = _json_stamp(target)
    if std.get("version") != json_stamp:
        ok = fail(f"G0 JSON version {json_stamp}")
    blob = spec + ru + json.dumps(std)
    if "way-v0.1.3" not in blob:
        ok = fail("G0 schema_version frozen marker missing")
    if re.search(r'"states"\s*:\s*\[[^\]]*masked', blob) or \
            re.search(r'"status_enum"\s*:\s*\[[^\]]*masked', blob):
        ok = fail("G0 masked present in states/status_enum")
    # Previous release stamps outside §7 history: only exact stamp forms
    # (H1/Status display forms + full three-part stamp) are stale markers;
    # bare short-form prose references (e.g. 'deferred to v0.2') stay legal
    # for G0 -- the strict forward-ref check on those lives in G7 (active
    # from target 0.4).
    stale = [f"# MAQS-Way v{prev_display} ", f"**Status:** v{prev_display} ",
             f"**Статус:** v{prev_display} ", f"v{prev}", prev]
    for name, text in (("SPEC.md", spec), ("SPEC-RU.md", ru)):
        pre_history = text.split("## 7.")[0] if "## 7." in text else text
        for tok in stale:
            if tok in pre_history:
                ok = fail(f"G0 stale {tok!r} outside §7 in {name}")
    if ok:
        print(f"G0 ok (stamps v{target} / JSON {json_stamp} / model frozen / masked absent)")
    return ok


def check_g3():
    sys.path.insert(0, str(ROOT / "schemas"))
    import maqs_way_audit
    rep = maqs_way_audit.run_all(quiet=True)
    green = rep.pop("_green")
    if not green:
        print("GATE RED — G3 audit all not green")
        return False
    manifest = json.loads((ROOT / "conformance" / "manifest.json").read_text())
    if len(manifest) != 12:
        return fail("G3 manifest count != 12")
    land = (ROOT / "docs" / "landscape.md").read_text()
    if "verified" not in land:
        return fail("G3 landscape verified column missing")
    print("G3 ok (audit GREEN, manifest 12, landscape column present; "
          "link liveness owner-verified)")
    return True


def check_g4(target, prev_display):
    spec = (ROOT / "SPEC.md").read_text()
    entry = f"{prev_display} → v{target}"
    if entry not in spec:
        return fail(f"G4 §7 {prev_display}→v{target} entry missing")
    window = spec.split(entry, 1)[1][:2500]
    for gap in ("B4", "E10", "I10", "I14", "I15", "P9", "0.6a"):
        if gap not in window:
            return fail(f"G4 §7 entry omits open gap {gap} (silence = false green)")
    print(f"G4 ok (§7 entry {prev_display}→v{target} present WITH open-gap list)")
    return True


def check_g5(target):
    bad = []
    gate = re.compile(r"^v" + re.escape(target) + r"(?![\d.])")
    for path in sorted((ROOT / "schemas").glob("*.json")):
        if path.name in ("maqs-way-standard.json", "baseline.json"):
            continue
        text = path.read_text()
        for m in re.finditer(r'"closes_in"\s*:\s*"([^"]*)"', text):
            if gate.match(m.group(1)) and "v0.3" not in m.group(1):
                bad.append(f"{path.name}: {m.group(1)[:60]}")
    if bad:
        for b in bad:
            print(f"GATE RED — G5 gap targets THIS release without closure: {b}")
        return False
    print(f"G5 ok (no known gap targets v{target} without closure)")
    return True


def check_g6():
    """G6 hygiene-all-green: run ALL schemas/check_*.py except this script.

    Owner amendment (v0.3 step 8): self-exclusion (no infinite self-run);
    scripts run WITHOUT arguments; criterion = exit code (0 = pass,
    including 'GREEN with advisory/known gap'; non-zero = RED); a script
    requiring arguments or crashing = RED with its name, no silent skips;
    the output lists every run script and its result.
    """
    bad, ran = [], 0
    for s in sorted((ROOT / "schemas").glob("check_*.py")):
        if s.name == "check_release.py":
            continue  # self-exclusion (owner amendment)
        r = subprocess.run([sys.executable, str(s)], capture_output=True,
                           text=True, cwd=ROOT)
        ran += 1
        status = "GREEN" if r.returncode == 0 else "RED"
        print(f"G6 {status}: {s.name}")
        if r.returncode != 0:
            bad.append(s.name)
    if bad:
        print(f"GATE RED — G6 failing gates: {', '.join(bad)}")
        return False
    print(f"G6 ok ({ran} gates green, self-excluded: check_release.py)")
    return True


# G7 pattern list (owner task 2026-10-29, fixed formulations; RU
# extensions per the stale-refs application amendment): the marker
# phrase must be followed by the pinned version (captured in full, v0.N
# or v0.N.P, for the numeric ref<=target comparison).
_G7_RE = re.compile(
    r"(?:TODO|deferred to|to be added in|planned for|planned in|closes in|"
    r"отложено до|будет добавлено в|запланировано (?:на|в)|"
    r"перенесен[аоы]? в|будет добавлен[аоы]? в|отложен[аоы]? до)"
    r"\s+v(\d+(?:\.\d+)*)")


def _ver_tuple(version: str):
    """'0.2' -> (0, 2, 0); '0.2.1' -> (0, 2, 1). Numeric comparison only."""
    parts = [int(p) for p in version.split(".")]
    return tuple(parts + [0] * (3 - len(parts)))


def check_g7(target, files=None):
    """G7 forward refs to released versions: promises outside §7 addressed
    to a version <= target are stale by the time target ships. Active from
    target 0.4; below that, a skip line and no effect on the verdict.

    files: iterable of (display_name, Path) scanned pairs; defaults to the
    canon pair in ROOT. Overridable so the RED self-test can run G7 on a
    temp copy of SPEC.md outside the repo (mechanics as in the evidence
    repo negative-red/replay_red.py) without touching the canon.
    """
    if _ver_tuple(target) < (0, 4, 0):
        print("G7 skipped (active from v0.4; v0.3 verdict stays reproducible)")
        return True
    if files is None:
        files = (("SPEC.md", ROOT / "SPEC.md"),
                 ("SPEC-RU.md", ROOT / "SPEC-RU.md"))
    bad = []
    for name, path in files:
        text = path.read_text()
        pre_history = text.split("## 7.")[0] if "## 7." in text else text
        for lineno, line in enumerate(pre_history.splitlines(), 1):
            for m in _G7_RE.finditer(line):
                ref = _ver_tuple(m.group(1))
                if ref <= _ver_tuple(target):
                    bad.append((name, lineno, f"v{m.group(1)}", m.group(0).strip()))
    if bad:
        for name, lineno, ref, quote in bad:
            print(f"GATE RED — G7 forward ref to released {ref} in "
                  f"{name}:{lineno}: {quote}")
        return False
    print("G7 ok (no forward refs to released versions outside §7)")
    return True


# G8 (owner task 2026-11-11): single source for the declared MAQS version.
# The tracked files whose MAQS mentions must agree with the canon field.
G8_FILES = ("SPEC.md", "SPEC-RU.md", "maqs-way-standard.json",
            "docs/mapping-to-maqs.md", "README.md")
# A mention is a standalone version token: "MAQS 0.5a" is an item id, not a
# version, so the match must not run into a letter or another dot.
_G8_MENTION_RE = re.compile(r"MAQS v?(\d+\.\d+(?:\.\d+)?)(?![\w.])")
_G8_SYNC_AFTER_RE = re.compile(r"\s+sync\b", re.I)
# RU mirror of exception 2: the sync phrase precedes the version there
# ("Из синхронизации MAQS 1.8.1 (...)"), same historical mention as the EN
# "MAQS 1.8.1 sync".
_G8_SYNC_BEFORE_RE = re.compile(r"(?:sync|синхронизаци\w*)\s*$", re.I)
_G8_TICKS_RE = re.compile(r"`[^`]*`")


def _g8_mentions(line):
    """Yield (start, end, version) for standalone MAQS mentions on a line."""
    for m in _G8_MENTION_RE.finditer(line):
        yield m.start(), m.end(), m.group(1)


def check_g8(files=None, canon_path=None):
    """G8: every MAQS version mention equals maqs_core_reference.

    files: iterable of (display_name, Path) pairs; defaults to G8_FILES in
    ROOT. canon_path overrides the JSON carrying the single source. Both are
    overridable so the self-test can run G8 on temp copies outside the repo
    (mechanics as in the evidence repo negative-red/replay_red.py) without
    touching the canon.
    """
    canon_path = Path(canon_path) if canon_path is not None \
        else ROOT / "maqs-way-standard.json"
    try:
        std = json.loads(canon_path.read_text())
    except (OSError, ValueError) as exc:
        return fail(f"G8 source unreadable: {canon_path.name}: {exc}")
    ref = std.get("maqs_core_reference") if isinstance(std, dict) else None
    if not ref:
        return fail("G8 source missing: maqs-way-standard.json has no "
                    "maqs_core_reference field (single source of the "
                    "declared MAQS version)")
    src = _G8_MENTION_RE.search(str(ref))
    if not src:
        return fail("G8 source version not extractable: maqs_core_reference "
                    f"carries no 'MAQS <version>' token ({str(ref)[:80]!r})")
    canon_v = src.group(1)
    canon_t = _ver_tuple(canon_v)
    if files is None:
        files = [(name, ROOT / name) for name in G8_FILES]
    bad, seen = [], 0
    for name, path in files:
        text = Path(path).read_text()
        pre_history = text.split("## 7.")[0] if "## 7." in text else text
        for lineno, line in enumerate(pre_history.splitlines(), 1):
            ticks = [s.span() for s in _G8_TICKS_RE.finditer(line)]
            for start, end, ver in _g8_mentions(line):
                if any(a <= start < b for a, b in ticks):
                    continue  # exception 1: file name / path in backticks
                if _G8_SYNC_AFTER_RE.match(line[end:]) or \
                        _G8_SYNC_BEFORE_RE.search(line[:start]):
                    continue  # exception 2: historical sync phrase
                seen += 1
                if _ver_tuple(ver) != canon_t:
                    bad.append((name, lineno, line[start:end], canon_v))
    if bad:
        for name, lineno, found, cv in bad:
            print(f"GATE RED — G8 MAQS version mismatch in {name}:{lineno}: "
                  f"found {found}, canon declares MAQS v{cv} "
                  f"(maqs-way-standard.json maqs_core_reference)")
        return False
    print(f"G8 ok ({seen} MAQS mentions across {len(files)} files equal "
          f"MAQS v{canon_v}; single source: maqs_core_reference)")
    return True


_G8_SANDBOX_PATHS = ("SPEC.md", "SPEC-RU.md", "maqs-way-standard.json",
                     "docs/mapping-to-maqs.md", "README.md",
                     "schemas/check_release.py")


def _g8_sandbox():
    """Temp copy of the G8 inputs OUTSIDE the repo (canon never modified)."""
    import shutil
    import tempfile
    root = Path(tempfile.mkdtemp(prefix="maqs_g8_")) / "canon"
    for rel in _G8_SANDBOX_PATHS:
        dst = root / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(ROOT / rel, dst)
    return root


def _g8_run(root):
    r = subprocess.run([sys.executable, str(root / "schemas" / "check_release.py"),
                        "--only", "g8", "--target", "0.3", "--prev", "0.2.1"],
                       capture_output=True, text=True)
    return r.returncode, r.stdout + r.stderr


def self_test_g8() -> int:
    """Three G8 shapes on temp copies outside the repo (exit 0 = all behave).

    1. GREEN baseline (historical 'MAQS 1.8.1 sync' / RU mirror untouched):
       exit 0, zero findings.
    2. one substantive mention flipped to 'MAQS v1.8.1': exit 1, exactly one
       mismatch line, with the file and line number.
    3. JSON without maqs_core_reference: exit 1, explicit missing-source
       message.
    """
    import shutil
    ok = True

    root = _g8_sandbox()
    try:
        rc, out = _g8_run(root)
        hits = out.count("G8 MAQS version mismatch")
        good = rc == 0 and hits == 0
        print(f"SELF-TEST G8/1 historical sync mention untouched: "
              f"{'PASS' if good else 'FAIL'} (exit {rc}, {hits} findings)")
        ok &= good
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)

    root = _g8_sandbox()
    try:
        spec = root / "SPEC.md"
        text = spec.read_text()
        needle = "MAQS v1.9 remains technical audit core"
        lineno = text[:text.index(needle)].count("\n") + 1
        spec.write_text(text.replace(needle,
                                     "MAQS v1.8.1 remains technical audit core",
                                     1))
        rc, out = _g8_run(root)
        hits = out.count("G8 MAQS version mismatch")
        named = f"in SPEC.md:{lineno}:" in out
        good = rc == 1 and hits == 1 and named
        print(f"SELF-TEST G8/2 one mention -> MAQS v1.8.1: "
              f"{'PASS' if good else 'FAIL'} (exit {rc}, {hits} findings, "
              f"SPEC.md:{lineno} named: {named})")
        ok &= good
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)

    root = _g8_sandbox()
    try:
        std_path = root / "maqs-way-standard.json"
        std = json.loads(std_path.read_text())
        del std["maqs_core_reference"]
        std_path.write_text(json.dumps(std, indent=2, ensure_ascii=False))
        rc, out = _g8_run(root)
        good = rc == 1 and "G8 source missing" in out and \
            "maqs_core_reference" in out
        print(f"SELF-TEST G8/3 JSON without maqs_core_reference: "
              f"{'PASS' if good else 'FAIL'} (exit {rc}, "
              f"{'missing-source message' if good else out.strip()[:160]})")
        ok &= good
    finally:
        shutil.rmtree(root.parent, ignore_errors=True)

    print("SELF-TEST G8: " + ("all three shapes behave" if ok else "FAILED"))
    return 0 if ok else 1


def main() -> int:
    ap = argparse.ArgumentParser(description="MAQS-Way release gate (G0/G3/G4/G5/G6/G7/G8)")
    ap.add_argument("--target", default=DEFAULT_TARGET,
                    help="release stamp to verify (default: %(default)s)")
    ap.add_argument("--prev", default=None,
                    help="previous release stamp for the stale checks "
                         "(default: auto-decremented --target)")
    ap.add_argument("--only", default=None,
                    help="comma-separated gate subset to run (e.g. g8); "
                         "default: all")
    ap.add_argument("--self-test", action="store_true",
                    help="run the G8 self-check on temp copies outside the repo")
    args = ap.parse_args()
    if args.self_test:
        return self_test_g8()
    target = args.target
    prev = args.prev if args.prev is not None else _prev_stamp(target)
    prev_display = _display(prev)
    results = []
    gates = [("G0", lambda: check_g0(target, prev, prev_display)),
             ("G3", check_g3),
             ("G4", lambda: check_g4(target, prev_display)),
             ("G5", lambda: check_g5(target)),
             ("G6", check_g6),
             ("G7", lambda: check_g7(target)),
             ("G8", check_g8)]
    if args.only:
        want = {g.strip().upper() for g in args.only.split(",") if g.strip()}
        gates = [(g, fn) for g, fn in gates if g in want]
    for name, fn in gates:
        results.append((name, fn()))
    print("G1/G2: MANUAL boundary (mirror + derivatives per release report)")
    if all(r for _, r in results):
        gate_names = "/".join(g for g, _ in results)
        print(f"RELEASE GREEN — v{target} shippable "
              f"({gate_names} executable; G1/G2 manual)")
        return 0
    print("GATE RED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
