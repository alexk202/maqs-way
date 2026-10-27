"""I10/I11/I12 counter gate (Way package 1.6a).

Formulation lives in proposals/i10-i12-counters.md (historical only;
normative text is in SPEC §3.4, canonized v0.3, owner signature 2026-10-27).

One mechanism: sliding/tumbling counter machines over synthetic event
streams (no infra). Alert sink is a REAL file journal (temp dir, H5):
probes read the trace AFTER halt — stderr/exit alone are not persistent.

Fixture checks (C8 pattern): three states + whitelist/fixture lockstep +
cross-ref — every entry points at the existing formulation file.

CLI integration point (documented, not implemented): `audit counters`
after v0.2 canonization. CLI 1.4 and gates 1.1–1.5 untouched.

Run: python3 schemas/check_i_counters.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "i_counters.json"

# Closed whitelist (C8 pattern): ONLY these ids may be known gaps.
# I10/I11/I12 closed by v0.3 canonization (SPEC §3.4, owner signature
# 2026-10-27; rules per owner amendment: LOG-3.4 anchors, I11 keeps MAQS:I11
# for the C8 bridge).
KNOWN_GAPS = set()

# Rule namespaces for covered entries (mirror of check_c8_coverage.py).
MAQS_VALID = {
    "0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "P",
    "E6", "F1", "F7", "G1", "I11",
}
LEGIT_NONP = {"LOG-3.4": "logging"}


class Counter:
    """Sliding/tumbling occurrence counter. Pure except the journal file."""

    def __init__(self, threshold, window_s, window_type, action, journal):
        self.threshold = threshold
        self.window_s = window_s
        self.window_type = window_type
        self.action = action
        self.journal = journal
        self.events = []  # (ts, signature)
        self.fired = []

    def record(self, ts, signature):
        self.events.append((ts, signature))
        if self.window_type == "sliding":
            cutoff = ts - self.window_s
            recent = [e for e in self.events if e[0] > cutoff and e[1] == signature]
        else:  # tumbling
            bucket = ts // self.window_s
            recent = [e for e in self.events
                      if e[0] // self.window_s == bucket and e[1] == signature]
        if len(recent) >= self.threshold:
            return self._fire(ts, signature, len(recent))
        return None

    def _fire(self, ts, signature, count):
        entry = {"ts": ts, "signature": signature, "count": count,
                 "action": self.action}
        if self.action == "aggregate":
            self.fired.append(("aggregated", entry))
        elif self.action == "halt":
            self.journal.write({"event": "halt+alert", **entry})
            self.fired.append(("halted", entry))
        elif self.action == "escalate":
            self.journal.write({"event": "escalated", **entry})
            self.fired.append(("escalated", entry))
        return self.fired[-1][0]


class Journal:
    """Append-only JSON-lines file (temp dir). Readable after halt."""

    def __init__(self):
        self.path = Path(tempfile.mkdtemp()) / "journal.jsonl"

    def write(self, entry):
        with open(self.path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def read_all(self):
        if not self.path.exists():
            return []
        return [json.loads(l) for l in self.path.read_text().splitlines()]


def b5_link(claimed_success, performed_sink):
    """I10->B5: claimed success with empty work-sink is a B5-failure."""
    if claimed_success and not performed_sink:
        return "B5-failure"
    return "ok"


def check_fixture():
    classes = json.loads(FIXTURE.read_text())
    standard = json.loads((ROOT / "maqs-way-standard.json").read_text())
    known_way = {p["id"] for p in standard["principles"]}
    fixture_gaps = {c["id"] for c in classes if c.get("known_gap")}
    if fixture_gaps != KNOWN_GAPS:
        print("GATE RED — whitelist/fixture mismatch:")
        print(f"  whitelist ({len(KNOWN_GAPS)}): {sorted(KNOWN_GAPS)}")
        print(f"  fixture   ({len(fixture_gaps)}): {sorted(fixture_gaps)}")
        return 1
    for c in classes:
        if not c.get("rules"):
            if not (c["id"] in KNOWN_GAPS and c.get("known_gap")
                    and c.get("owner") and c.get("closes_in")
                    and c.get("declared") and c.get("formulation")):
                print(f"GATE RED — malformed gap entry: {c.get('id')}")
                return 1
            form = c["formulation"].split("#")[0]
            if not (ROOT / form).exists():
                print(f"GATE RED — orphan formulation ref in {c['id']}")
                return 1
            d = c["declared"]
            if not all(k in d for k in ("threshold", "window", "key", "action")):
                print(f"GATE RED — declared triple incomplete in {c['id']}")
                return 1
            if not isinstance(d["window"], dict) or "type" not in d["window"]:
                print(f"GATE RED — window type undeclared in {c['id']}")
                return 1
            print(f"KNOWN GAP: {c['id']} (maqs {c.get('maqs')}) "
                  f"-> owner {c['owner']}, closes in {c['closes_in']}")
        elif c.get("known_gap"):
            print(f"BYPASS ATTEMPT (known_gap not in whitelist): {c['id']}")
            print("GATE RED")
            return 1
        else:
            rules = c.get("rules", [])
            bad = [r for r in rules if r not in known_way
                   and r not in LEGIT_NONP
                   and not (r.startswith("MAQS:") and r[5:] in MAQS_VALID)]
            if bad:
                print(f"UNKNOWN RULES in {c['id']}: {', '.join(bad)}")
                print("GATE RED")
                return 1
            print(f"COVERED: {c['id']} (canonized v0.3 → SPEC §3.4)")
    return 0


def check_semantics():
    fails = []

    # Probe 1: eternal restart without halt -> must halt at N=3.
    j = Journal()
    c = Counter(3, 600, "sliding", "halt", j)
    actions = [c.record(t, "exit=1") for t in (0, 100, 200, 300)]
    if "halted" not in actions:
        fails.append("probe1 eternal restart without halt")
    trace = j.read_all()
    if not any(e.get("event") == "halt+alert" for e in trace):
        fails.append("probe1 alert trace unreadable after halt (sink not persistent)")

    # Probe 2: eternal poll without escalate -> must escalate at N=3.
    j2 = Journal()
    c2 = Counter(3, 3600, "sliding", "escalate", j2)
    actions2 = [c2.record(t, "dep=db:conn-refused") for t in (0, 100, 200, 300)]
    if "escalated" not in actions2:
        fails.append("probe2 eternal poll without escalate")

    # Probe 3: aggregation emits counter (I10), different signatures never merge.
    j3 = Journal()
    c3 = Counter(3, 300, "sliding", "aggregate", j3)
    c3.record(0, "wA")
    c3.record(60, "wB")
    r = c3.record(120, "wA")
    if r is not None:
        fails.append("probe3 different signatures merged")
    c3.record(180, "wA")
    r2 = c3.record(240, "wA")
    if r2 != "aggregated":
        fails.append("probe3 aggregation without counter")

    # Probe 4: sliding vs tumbling distinguished (same stream, different verdicts).
    js, jt = Journal(), Journal()
    cs = Counter(2, 100, "sliding", "halt", js)
    ct = Counter(2, 100, "tumbling", "halt", jt)
    stream = (90, 110)  # straddles the t=100 bucket boundary
    rs = [cs.record(t, "x") for t in stream]
    rt = [ct.record(t, "x") for t in stream]
    if rs == rt:
        fails.append("probe4 sliding/tumbling indistinguishable")

    # Probe 5 (council e): claimed success + empty work-sink -> B5-failure.
    if b5_link(True, []) != "B5-failure":
        fails.append("probe5 claimed-success-without-work not flagged")
    if b5_link(True, ["job-1"]) != "ok":
        fails.append("probe5 performed work misflagged")

    # Probe 6: escalate repeats on schedule (not one-shot, not busy poll).
    j6 = Journal()
    c6 = Counter(2, 3600, "sliding", "escalate", j6)
    c6.record(0, "dep=q:timeout")
    first = c6.record(10, "dep=q:timeout")
    c6.record(3700, "dep=q:timeout")
    second = c6.record(3710, "dep=q:timeout")  # threshold re-met in new window
    if first != "escalated" or second != "escalated":
        fails.append("probe6 escalate not repeatable per window")

    for f in fails:
        print(f"GATE RED — {f}")
    return 1 if fails else 0


def main() -> int:
    if check_fixture() != 0:
        return 1
    if check_semantics() != 0:
        print("GATE RED")
        return 1
    print("COVERED 3/3 + KNOWN GAPS 0 (I10, I11, I12 canonized v0.3 → SPEC §3.4)")
    print("SEMANTICS 6/6 (halt, escalate, aggregate, sliding/tumbling, b5-link, repeat)")
    print("GATE GREEN")
    return 0


if __name__ == "__main__":
    sys.exit(main())
