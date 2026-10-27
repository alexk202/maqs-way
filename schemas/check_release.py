"""Release gate (Way package 1.8): G0/G3/G4/G5 executable.

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
G3 verifiability: audit all GREEN + manifest count 12 + landscape file
  present with verified column (link liveness itself is owner-verified).
G4 process purity: §7 carries the v{prev}→v{target} entry WITH the
  open-gap list.
G5 honesty (added 1.8): no known gap list targets THIS release version
  without proven closure. Silence about gaps = false green.

Run: python3 schemas/check_release.py [--target 0.2.1]
Exit 0 = releasable, 1 = red.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TARGET = "0.2.1"


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
    if std.get("version") != target:
        ok = fail(f"G0 JSON version {target}")
    blob = spec + ru + json.dumps(std)
    if "way-v0.1.3" not in blob:
        ok = fail("G0 schema_version frozen marker missing")
    if re.search(r'"states"\s*:\s*\[[^\]]*masked', blob) or \
            re.search(r'"status_enum"\s*:\s*\[[^\]]*masked', blob):
        ok = fail("G0 masked present in states/status_enum")
    # Previous release stamps outside §7 history: only exact stamp forms
    # (H1/Status display forms + full three-part stamp) are stale markers;
    # bare short-form prose references (e.g. 'deferred to v0.2') stay legal.
    stale = [f"# MAQS-Way v{prev_display} ", f"**Status:** v{prev_display} ",
             f"**Статус:** v{prev_display} ", f"v{prev}", prev]
    for name, text in (("SPEC.md", spec), ("SPEC-RU.md", ru)):
        pre_history = text.split("## 7.")[0] if "## 7." in text else text
        for tok in stale:
            if tok in pre_history:
                ok = fail(f"G0 stale {tok!r} outside §7 in {name}")
    if ok:
        print(f"G0 ok (stamps v{target} / JSON {target} / model frozen / masked absent)")
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


def main() -> int:
    ap = argparse.ArgumentParser(description="MAQS-Way release gate (G0/G3/G4/G5)")
    ap.add_argument("--target", default=DEFAULT_TARGET,
                    help="release stamp to verify (default: %(default)s)")
    ap.add_argument("--prev", default=None,
                    help="previous release stamp for the stale checks "
                         "(default: auto-decremented --target)")
    args = ap.parse_args()
    target = args.target
    prev = args.prev if args.prev is not None else _prev_stamp(target)
    prev_display = _display(prev)
    results = [("G0", check_g0(target, prev, prev_display)),
               ("G3", check_g3()),
               ("G4", check_g4(target, prev_display)),
               ("G5", check_g5(target))]
    print("G1/G2: MANUAL boundary (mirror + derivatives per release report)")
    if all(r for _, r in results):
        print(f"RELEASE GREEN — v{target} shippable "
              f"(G0/G3/G4/G5 executable; G1/G2 manual)")
        return 0
    print("GATE RED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
