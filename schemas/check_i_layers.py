"""I15 layer gate (MAQS I15 [REC], Way package 1.6d).

Formulation lives in proposals/i15-layers.md (historical only;
normative text is in SPEC §3.4, canonized v0.3, owner signature 2026-10-27).

Core correction (review round): identify() READS the declared layer,
it does NOT infer it. Inferring a layer is a label without source -> RED.
No declaration -> unknown (loud) -> interpretation suspended.

Probes:
(a) undeclared layer -> unknown, never a guess;
(b) cross-layer verdict (foreign expectation on foreign answer) -> RED;
(c) bypass marker in fixture -> RED;
(d) silent default substitution (quiet session) -> RED;
(e) inference attempt (heuristic guessing) -> RED.
(f) unknown without loud event -> RED (quiet unknown = silent-fail).

CLI integration point (documented, not implemented): `audit layers`
after v0.2 canonization. CLI 1.4 and gates 1.1–1.6c untouched.

Run: python3 schemas/check_i_layers.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "i_layers.json"

# Closed whitelist: ONLY these ids may be known gaps. I15 closed by v0.3
# canonization (SPEC §3.4, owner signature 2026-10-27, layer-field
# amendment); a known_gap true entry is now a BYPASS attempt.
KNOWN_GAPS = set()

# Rule namespaces for covered entries (mirror of check_c8_coverage.py).
MAQS_VALID = {
    "0", "A", "B", "C", "D", "E", "F", "G", "H", "I", "J", "K", "P",
    "E6", "F1", "F7", "G1", "I11",
}
LEGIT_NONP = {"LOG-3.4": "logging"}

LAYERS = {"persistent", "session", "transient"}

EXPECT = {
    "persistent": "verbatim-or-degradation",
    "session": "noise-expected",
    "transient": "bonus-not-evidence",
}


def identify(query):
    """READ the declared layer. Returns (layer|unknown, events).

    Any heuristic 'guessing' path is rejected by the caller contract:
    use declare() for declared metadata; guess() is the RED probe.
    """
    layer = (query.get("layer") or "").strip()
    if layer in LAYERS:
        return layer, []
    return "unknown", ["diagnostic event (LOG-3.4): layer unestablished"]


def interpret(layer, answer_quality):
    """Apply the DECLARED layer's expectations. Returns verdict string."""
    if layer == "unknown":
        return "suspended (no verdict)"
    if layer == "persistent":
        return "pass" if answer_quality == "verbatim" else "degradation"
    if layer == "session":
        return "pass"  # noise expected, never degradation
    if layer == "transient":
        return "bonus (not evidence)"
    raise ValueError(f"undeclared layer in interpreter: {layer!r}")


def check_fixture():
    doc = json.loads(FIXTURE.read_text())
    item = doc.get("item", {})
    if set(doc.get("layers", [])) != LAYERS:
        print("GATE RED — taxonomy is not exactly {persistent, session, transient}")
        return 1
    if item.get("known_gap"):
        if item.get("id") not in KNOWN_GAPS:
            print(f"BYPASS ATTEMPT (known_gap not in whitelist): {item.get('id')}")
            print("GATE RED")
            return 1
        if not (item.get("owner") and item.get("closes_in") and item.get("formulation")):
            print("GATE RED — gap malformed (owner/closes_in/formulation required)")
            return 1
        form = item["formulation"].split("#")[0]
        if not (ROOT / form).exists():
            print("GATE RED — orphan formulation ref")
            return 1
        print(f"KNOWN GAP: I15 (maqs I15 [REC]) -> owner {item['owner']}, "
              f"closes in {item['closes_in']}")
        return 0
    # Covered branch (canonized v0.3): rules must resolve to real anchors.
    rules = item.get("rules", [])
    standard = json.loads((ROOT / "maqs-way-standard.json").read_text())
    known_way = {p["id"] for p in standard["principles"]}
    bad = [r for r in rules if r not in known_way and r not in LEGIT_NONP
           and not (r.startswith("MAQS:") and r[5:] in MAQS_VALID)]
    if bad:
        print(f"UNKNOWN RULES in {item.get('id')}: {', '.join(bad)}")
        print("GATE RED")
        return 1
    print("COVERED: I15 (canonized v0.3 → SPEC §3.4)")
    return 0


def check_semantics():
    fails = []

    # Probe (a): undeclared -> unknown, never a guess.
    layer, events = identify({})
    if layer != "unknown" or not events:
        fails.append("probe-a undeclared layer must yield loud unknown")

    # Probe (b): cross-layer verdict -> RED (session noise read as persistent).
    if interpret("persistent", "noisy") != "degradation":
        fails.append("probe-b persistent deviation must read degradation")
    if interpret("session", "noisy") != "pass":
        fails.append("probe-b session noise misread as degradation")

    # Probe (d): silent default substitution forbidden: no quiet 'session'.
    layer_d, _ = identify({"layer": ""})
    if layer_d != "unknown":
        fails.append("probe-d empty declaration must not default (quiet session)")

    # Probe (e): inference rejected — heuristic hints without declared layer
    # must yield unknown, never a guessed layer.
    layer_e, _ = identify({"text": "old long memory", "hint": "looks persistent",
                           "source": "session_cache"})
    if layer_e != "unknown":
        fails.append("probe-e heuristic hints must not infer a layer")

    # Probe (f): unknown without loud event -> RED.
    _, ev = identify({"note": "no layer field"})
    if not ev:
        fails.append("probe-f quiet unknown (no diagnostic event)")

    for f in fails:
        print(f"GATE RED — {f}")
    return 1 if fails else 0


def main() -> int:
    if check_fixture() != 0:
        return 1
    if check_semantics() != 0:
        print("GATE RED")
        return 1
    # Declared read path (green path): declared persistent + verbatim.
    layer, _ = identify({"layer": "persistent"})
    if layer != "persistent" or interpret(layer, "verbatim") != "pass":
        print("GATE RED — declared read path broken")
        print("GATE RED")
        return 1
    print("COVERED 1/1 + KNOWN GAPS 0 (I15 canonized v0.3 → SPEC §3.4)")
    print("SEMANTICS: read-not-infer enforced; unknown loud; expectations bound")
    print("GATE GREEN (I15 [REC] advisory — reported-not-failing)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
