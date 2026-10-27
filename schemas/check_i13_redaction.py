"""I13 secret-guard gate (MAQS I13 [CRIT], Way package 1.6b).

Proves the existing norm, introduces none: SPEC §3.4 redactor + JSON
logging sanitization. Test checks EXACTLY §3.4+JSON, not one line more:
sinks = log-record strings (log writes + OTel details). stderr/traceback
beyond §3.4 are out of scope — testing them would establish "§3.4+".

Semantics is mask-before-write: emit() redacts BEFORE sink.append().
Probe (e) distinguishes it from post-scan: a deliberately broken emitter
(raw append) MUST be caught by audit_sink() as residue-found RED.

Secrets are synthetic sentinels ONLY (sk-TEST-NOT-REAL-*, botTEST:AA...).
Production-shaped credential strings MUST NOT appear in fixtures — enforced
by check_no_real_secrets() below, not by agreement. H5 restated: committed literals
are inert sentinels (never valid credentials, no scanner-validatable);
no live stores are touched; temp only at runtime.

Vector 'urlp_glued' (MAQS 1.8.1 sync): the path-embedded form glued into a
URL path after an identifier (/bot<id>:AA.../getUpdates) — the prefix-adjacent
context of the I13 1.8 expansion. Norm pre-exists in §3.4 ("credential-in-URL
... in path"); the regexes carry no boundary anchors, the vector proves it.

Integration contract (documented, NOT implemented — precedent 1.5):
  'audit secrets': no args; runs this gate; exit 0/1; text report to stdout.
  CLI 1.4 untouched by package 1.6b.

Run: python3 schemas/check_i13_redaction.py
Exit 0 = no hard failures, 1 = red.
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FIXTURE = ROOT / "schemas" / "i_guards.json"
STANDARD = ROOT / "maqs-way-standard.json"
SPEC = ROOT / "SPEC.md"

# Closed legit non-principle rules (B-gate pattern): suffix -> JSON path.
LEGIT_NONP = {"LOG-3.4": "logging"}
KNOWN_GAPS = set()  # empty: I13 is covered, any known_gap = bypass RED

SECRET_KV = re.compile(
    r"(?i)\b(api_key|api-key|token|secret|password|passwd)\b\s*[:=]\s*"
    r"(\"[^\"']+\"|'[^\"']+'|\S+)"
)
URL_QUERY = re.compile(r"([?&](?:token|key|secret|password)=)[^&\s\"']+")
URL_PATH_BOT = re.compile(r"bot[A-Za-z0-9]*:AA[A-Za-z0-9_-]{6,}")
SENTINEL_RESIDUE = re.compile(r"sk-TEST-NOT-REAL-\S+|botTEST:AA\S+")
REAL_PATTERN = re.compile(r"sk-prod-|bot\d+:AA[A-Za-z0-9_-]{10,}")  # pattern-def

ALLOWED_KEYS = ("tool_args_sanitized", "retrieval_count",
                "policy_decision", "latency_ms")


def redact(text):
    text = SECRET_KV.sub(lambda m: m.group(0).split(m.group(2))[0] + "***", text)
    text = URL_QUERY.sub(r"\1***", text)
    text = URL_PATH_BOT.sub("bot<id>:AA***", text)
    return text


def emit(sink, text):
    """Mask-before-write: redact happens BEFORE sink.append()."""
    sink.append(redact(text))


def emit_broken(sink, text):
    """Deliberately broken path (post-scan simulation): raw append."""
    sink.append(text)


def audit_sink(sink):
    """Post-hoc residue scan. Returns list of findings (empty = clean).

    Already-masked values ('***') are NOT residue: the query-pattern check
    skips matches whose captured value is exactly the mask marker.
    """
    findings = []
    for i, line in enumerate(sink):
        if SENTINEL_RESIDUE.search(line):
            findings.append(f"residue in sink[{i}]: {line[:80]}")
            continue
        for m in URL_QUERY.finditer(line):
            if not m.group(0).endswith("=***"):
                findings.append(f"residue in sink[{i}]: {line[:80]}")
                break
    return findings


def check_fixture():
    classes = json.loads(FIXTURE.read_text())
    standard = json.loads(STANDARD.read_text())
    known_way = {p["id"] for p in standard["principles"]}
    # Anchor: canon line must exist (council: no canon line -> test establishes norm).
    spec = SPEC.read_text()
    if "MAQS I13" not in spec:
        print("GATE RED — anchor missing: no 'MAQS I13' line in SPEC.md")
        return 1
    fixture_gaps = {c["id"] for c in classes if c.get("known_gap")}
    if fixture_gaps != KNOWN_GAPS:
        print("GATE RED — whitelist/fixture mismatch (whitelist is empty):")
        print(f"  fixture gaps: {sorted(fixture_gaps)}")
        return 1
    for c in classes:
        if c.get("known_gap"):
            print(f"BYPASS ATTEMPT (known_gap not in whitelist): {c['id']}")
            print("GATE RED")
            return 1
        bad = [r for r in c.get("rules", [])
               if r not in known_way and r not in LEGIT_NONP]
        if bad or not c.get("rules"):
            print(f"GATE RED — bad/empty rules in {c['id']}: {bad}")
            return 1
    # LEGIT_NONP targets must resolve (B-gate lock).
    for rule, path in LEGIT_NONP.items():
        node = standard
        for part in path.split("."):
            node = node.get(part) if isinstance(node, dict) else None
        if node is None:
            print(f"GATE RED — legit rule {rule} has no target '{path}'")
            return 1
    print("COVERED 1/1 (I13 — covered-by-canon, proven here)")
    return 0


VEC = {
    "plain": 'api_key=sk-TEST-NOT-REAL-abc123 user=alice',
    "urlq": 'GET /x?token=sk-TEST-NOT-REAL-zzz&u=1',
    "urlp": 'call botTEST:AA999fasdf path /send',
    "urlp_glued": 'GET https://api.example.org/botTEST:AA999fasdf/getUpdates HTTP/1.1',
    "allowed": 'tool_args_sanitized ok retrieval_count=3 policy_decision=BLOCK latency_ms=12',
}


def check_semantics():
    fails = []

    # Probe (a): plaintext secret must not pass.
    sink = []
    emit(sink, VEC["plain"])
    if audit_sink(sink):
        fails.append("probe-a plaintext secret residue after emit")

    # Probe (b): both credential-in-URL forms masked, incl. the prefix-glued
    # URL-path form (token after an identifier, no free-standing boundaries).
    sink = []
    emit(sink, VEC["urlq"])
    emit(sink, VEC["urlp"])
    emit(sink, VEC["urlp_glued"])
    if audit_sink(sink):
        fails.append("probe-b credential-in-URL residue after emit")

    # Probe (c): over-redaction is RED (allowed keys must pass verbatim).
    sink = []
    emit(sink, VEC["allowed"])
    if sink != [VEC["allowed"]]:
        fails.append("probe-c over-redaction: allowed keys altered")

    # Probe (e): broken (mask-after-write) path MUST be caught as residue RED.
    sink = []
    emit_broken(sink, VEC["plain"])
    if not audit_sink(sink):
        fails.append("probe-e broken emitter not caught (mask-before-write unproven)")

    for f in fails:
        print(f"GATE RED — {f}")
    return 1 if fails else 0


def check_no_real_secrets():
    """Static guard: no real credential patterns anywhere in this package's fixtures."""
    for rel in ("schemas/check_i13_redaction.py", "schemas/i_guards.json"):
        for line in (ROOT / rel).read_text().splitlines():
            if "pattern-def" in line:
                continue  # the guard's own definition (not a fixture secret)
            for m in REAL_PATTERN.finditer(line):
                print(f"GATE RED — real credential pattern in {rel}: {m.group(0)[:20]}")
                return 1
    return 0


def main() -> int:
    for check in (check_no_real_secrets, check_fixture, check_semantics):
        if check() != 0:
            print("GATE RED")
            return 1
    print("SEMANTICS 4/4 (plain-block, url-3-forms incl. prefix-glued, no-overredact, broken-caught)")
    print("GATE GREEN — I13 proven (norm pre-exists in §3.4)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
