"""Release gate v0.2 (Way package 1.8): G0/G3/G4/G5 executable.

G0 canon integrity: H1/Status v0.2 (EN/RU), JSON version 0.2.0,
  schema_version frozen (way-v0.1.3 present, no bump), `masked` absent
  from states/status_enum, old versions only in §7 history.
G1/G2 (mirror + derivatives): MANUAL checklist boundary — stated, not
  pretended executable. See release report.
Manual release-sync items (owner, together with the release):
  - CITATION.cff: bump version + date-released to the release stamp
    (free commit, same release window; never silently between releases).
G3 verifiability: audit all GREEN + manifest count 12 + landscape file
  present with verified column (link liveness itself is owner-verified).
G4 process purity: §7 carries the v0.1.4→v0.2 entry WITH the open-gap list.
G5 honesty (added 1.8): no known gap lists closes_in == THIS release
  version without proven closure. Silence about gaps = false green.

Run: python3 schemas/check_release.py
Exit 0 = releasable, 1 = red.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RELEASE = "0.2"


def fail(msg):
    print(f"GATE RED — {msg}")
    return False


def check_g0():
    ok = True
    spec = (ROOT / "SPEC.md").read_text()
    ru = (ROOT / "SPEC-RU.md").read_text()
    if "# MAQS-Way v0.2 " not in spec or "**Status:** v0.2" not in spec:
        ok = fail("G0 EN stamps (H1/Status v0.2)")
    if "# MAQS-Way v0.2 " not in ru or "**Статус:** v0.2" not in ru:
        ok = fail("G0 RU stamps (H1/Status v0.2)")
    std = json.loads((ROOT / "maqs-way-standard.json").read_text())
    if std.get("version") != "0.2.0":
        ok = fail("G0 JSON version 0.2.0")
    blob = spec + ru + json.dumps(std)
    if "way-v0.1.3" not in blob:
        ok = fail("G0 schema_version frozen marker missing")
    if re.search(r'"states"\s*:\s*\[[^\]]*masked', blob) or \
            re.search(r'"status_enum"\s*:\s*\[[^\]]*masked', blob):
        ok = fail("G0 masked present in states/status_enum")
    # Old versions outside §7 history: allow only in Change-Log section.
    for name, text in (("SPEC.md", spec), ("SPEC-RU.md", ru)):
        pre_history = text.split("## 7.")[0] if "## 7." in text else text
        if "v0.1.4" in pre_history or "0.1.4" in pre_history:
            ok = fail(f"G0 stale v0.1.4 outside §7 in {name}")
    if ok:
        print("G0 ok (stamps v0.2 / JSON 0.2.0 / model frozen / masked absent)")
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


def check_g4():
    spec = (ROOT / "SPEC.md").read_text()
    if "v0.1.4 → v0.2" not in spec and "v0.1.4 → v0.2" not in spec:
        return fail("G4 §7 v0.1.4→v0.2 entry missing")
    entry = spec.split("v0.1.4 → v0.2", 1)[1][:1500]
    for gap in ("B4", "E10", "I10", "I14", "I15", "P9", "0.6a"):
        if gap not in entry:
            return fail(f"G4 §7 entry omits open gap {gap} (silence = false green)")
    print("G4 ok (§7 entry present WITH open-gap list)")
    return True


def check_g5():
    bad = []
    for path in sorted((ROOT / "schemas").glob("*.json")):
        if path.name in ("maqs-way-standard.json", "baseline.json"):
            continue
        text = path.read_text()
        for m in re.finditer(r'"closes_in"\s*:\s*"([^"]*)"', text):
            if f"v{RELEASE}" in m.group(1) and "v0.3" not in m.group(1):
                bad.append(f"{path.name}: {m.group(1)[:60]}")
    if bad:
        for b in bad:
            print(f"GATE RED — G5 gap targets THIS release without closure: {b}")
        return False
    print("G5 ok (no known gap targets v0.2 without closure)")
    return True


def main() -> int:
    results = [("G0", check_g0()), ("G3", check_g3()),
               ("G4", check_g4()), ("G5", check_g5())]
    print("G1/G2: MANUAL boundary (mirror + derivatives per release report)")
    if all(r for _, r in results):
        print("RELEASE GREEN — v0.2 shippable (G0/G3/G4/G5 executable; G1/G2 manual)")
        return 0
    print("GATE RED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
