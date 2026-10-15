"""I14 handler-registry gate (MAQS I14 [REC], Way package 1.6c).

Formulation lives in proposals/i14-handlers.md (NOT canon).
I14 is a known gap (owner: 1.6c-formulation, closes_in: v0.2 canonization).

Verdict model (two levels):
- probe level: inconsistency inside the declared catalog is STRICT
  (orphan class, dead handler, path-into-void -> RED lines, exit 1).
- gate level: [REC]-findings are reported-not-failing; the report NAMES
  every finding and carries the advisory flag. "0 findings" and
  "check not run" are distinguished. Catalog completeness itself is
  NOT gated (declared scope).

CLI integration point (documented, not implemented): `audit handlers`
after v0.2 canonization. CLI 1.4 and gates 1.1–1.6b untouched.

Run: python3 schemas/check_i_handlers.py
Exit 0 = no hard failures (advisory findings named), 1 = red.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "i_handlers.json"

KNOWN_GAPS = {"I14"}  # the item itself stays a gap until v0.2


def load():
    return json.loads(FIXTURE.read_text())


def check_registry(doc):
    """Strict consistency inside the declared catalog. Returns findings list."""
    findings = []
    item = doc["item"]
    if item.get("known_gap"):
        if item["id"] not in KNOWN_GAPS:
            return None, [f"BYPASS ATTEMPT (known_gap not in whitelist): {item['id']}"]
        if not (item.get("owner") and item.get("closes_in")):
            return None, ["GAP-MALFORMED (no owner/closes_in)"]
    recipients = set(doc.get("recipients", []))
    seen_classes = set()
    for c in doc.get("classes", []):
        seen_classes.add(c["class"])
        reaction = c.get("reaction", {})
        has_handler = bool(reaction.get("handler"))
        path = reaction.get("escalation_path")
        # Probe (a): orphan class (neither handler nor path).
        if not has_handler and not path:
            findings.append(f"orphan-class (no reaction): {c['class']}")
        # Probe (d): path-into-void (target outside declared recipients).
        if path and path.get("target") not in recipients:
            findings.append(f"path-into-void: {c['class']} -> {path.get('target')}")
    return seen_classes, findings


def check_dead_handlers(doc, seen):
    """Probe (b): standalone handler with no catalog class (dead code)."""
    findings = []
    known = set(seen or []) | {c["class"] for c in doc.get("classes", [])}
    for h in doc.get("standalone_handlers", []):
        target = h.get("handles")
        if target not in known:
            findings.append(f"dead-handler (no catalog class): {h.get('id')} -> {target}")
    return findings


def build_report(doc, findings):
    """Report MUST enumerate findings (probe e: silent swallow forbidden)."""
    return {
        "item": doc["item"]["id"],
        "status": "known_gap",
        "advisory": "I14 [REC] — reported-not-failing",
        "checked_classes": len(doc.get("classes", [])),
        "completeness_claimed": False,
        "findings": sorted(findings),
        "findings_count": len(findings),
    }


def check_semantics():
    """Probe level (unit): hostile synthetic registries MUST be flagged.

    Proves the probes can fail (exit 1 on miss). Distinct from gate level,
    where real-fixture findings are named but non-blocking ([REC]).
    """
    hostile = {
        "item": {"id": "I14"},
        "recipients": ["owner"],
        "standalone_handlers": [{"id": "h-ghost", "handles": "syn.nonexistent"}],
        "classes": [
            {"class": "syn.orphan", "reaction": {}},
            {"class": "syn.void", "reaction": {"escalation_path": {"target": "void"}}},
            {"class": "syn.ok", "reaction": {"handler": "local_fix"}},
        ],
    }
    seen, findings = check_registry(hostile)
    joined = " ".join(findings)
    misses = []
    if not any("orphan-class" in f and "syn.orphan" in f for f in findings):
        misses.append("probe-a orphan not flagged")
    if not any("path-into-void" in f and "syn.void" in f for f in findings):
        misses.append("probe-d void path not flagged")
    findings += check_dead_handlers(hostile, seen)
    if not any("dead-handler" in f for f in findings):
        misses.append("probe-b dead handler not flagged")
    for m in misses:
        print(f"GATE RED — {m}")
    return 1 if misses else 0


def main() -> int:
    doc = load()
    if check_semantics() != 0:
        print("GATE RED")
        return 1
    seen, findings = check_registry(doc)
    if seen is None:  # bypass
        for f in findings:
            print(f"GATE RED — {f}")
        print("GATE RED")
        return 1
    findings += check_dead_handlers(doc, seen)
    rep = build_report(doc, findings)
    # Probe (e): report must contain every finding (swallow forbidden).
    if sorted(rep["findings"]) != sorted(findings) or \
            rep["findings_count"] != len(findings):
        print("GATE RED — gate-swallow: report dropped a finding")
        print("GATE RED")
        return 1
    print(f"KNOWN GAP: I14 (maqs I14 [REC]) -> owner {doc['item']['owner']}, "
          f"closes in {doc['item']['closes_in']}")
    print(f"REGISTRY checked {rep['checked_classes']} declared classes; "
          f"completeness NOT claimed")
    if findings:
        for f in findings:
            print(f"FINDING (advisory, named): {f}")
        print(f"FINDINGS: {len(findings)} named above (not folded, not blocking)")
    else:
        print("FINDINGS: 0 (check ran — distinct from check-not-run)")
    print("GATE GREEN with known gap (advisory I14 reported-not-failing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
