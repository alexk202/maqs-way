#!/usr/bin/env python3
"""H5 confound forensics (2026-10-25, no GPU, read-only).

Question the ТЗ asks: what did the SHARED live ~/.mem0/history.db do to the
frozen numbers (all runs before ffb5879 never set history_db_path)?

Mechanism (mem0 v2.2.1@0724291, verified in this session):
  Memory.add(infer=True) -> V3 phased pipeline: Phase 0 get_last_messages
  (main.py:922) feeds a "## Last k Messages" section of the extraction prompt
  (prompts.py:1037); Phase 8 save_messages (main.py:1207) writes the ingested
  session and then EVICTS everything but the 10 newest rows per scope
  (storage.py save_messages DELETE ... LIMIT 10). So the messages table is a
  sliding tail: at every add, the tail of the PREVIOUS add's session (previous
  question / previous run) entered the extraction prompt. All raw messages
  except each scope's final 10-row residue were evicted in flight.

Part 1a: reconstruct per run / per add-call what get_last_messages returned,
  by replaying every add of every run (order + chunking replicated from the
  runners) against an in-memory SQLite replicating storage.py SQL verbatim.
  Validated against the one recoverable ground truth: the live db's final
  per-scope residues (u_pilot, u_probe) must match the replay.
Part 1b: measure whether foreign-question entities reached the stores: a
  unique-shingle index (word 5-grams unique to exactly ONE question's
  haystack); every stored fact of question q carrying unique shingles of
  another question = cross-question leak. Sources: surviving /tmp stores
  (b4/g1/ii/b3-probe/g1-probes), the committed artifacts' texts
  (reppenalty, n5-family top5), and the history table's ADD events
  (all runs, including stores wiped by the Oct-23 reboot).

Writes evals/results/history_confound_forensics.{json,md}. Changes nothing
upstream; ~/.mem0 is only ever opened mode=ro&immutable=1.
"""
import hashlib
import json
import re
import shutil
import sqlite3
import sys
import time
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "datasets/longmemeval/longmemeval_oracle.json"
OUT = HERE / "results"
LIVE_DB = Path.home() / ".mem0" / "history.db"
WORK = Path("/tmp/opencode/forensics_work")  # temp copies of stores; never live

SINGLE_TYPES = ("single-session-user", "single-session-assistant",
                "single-session-preference")
N5_PICK = ["temporal-reasoning", "multi-session", "knowledge-update",
           "single-session-user", "single-session-assistant"]
CTX_LIMIT, CHARS_PER_TOK = 24000, 4.0

STORE_DIRS = {
    "b4": "/tmp/opencode/mem0single156b4_1792831463",
    "g1": "/tmp/opencode/mem0single156g1_1792838821",
    "ii": "/tmp/opencode/mem0single156ii_1792849233",
    "b3probe": "/tmp/opencode/mem0probe11_1792830762",
    "g1probes": "/tmp/opencode/g1probes_1792843713",
}

UNIQ = {}  # unique shingle map, filled in main before DP alignment

# ---------------------------------------------------------------------------
# dataset + run orders


def load_dataset():
    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in SINGLE_TYPES]
    assert len(singles) == 156, len(singles)
    n5pick = []
    for want in N5_PICK:
        n5pick.append(next(q for q in data if q["question_type"] == want))
    return data, singles, n5pick


def q_lookup(data):
    m = {}
    for q in data:
        qid = q["question_id"]
        m[qid] = q
        m[qid.split("_")[-1]] = q  # 8-hex suffix used by probe artifacts
        if not qid.startswith("gpt4_"):
            m["gpt4_" + qid] = q
    return m


def parts_of(sess):
    """Replicates the runner chunking (pilot_longmemeval_n5.py / pilot_lme_evidence.py)."""
    chars = sum(len(str(m.get("content", ""))) for m in sess)
    chunks = max(1, int(chars / (CTX_LIMIT * CHARS_PER_TOK)) + 1)
    size = max(1, len(sess) // chunks)
    out = []
    for ci in range(chunks):
        part = sess[ci * size:(ci + 1) * size] if chunks > 1 else sess
        if not part:
            continue
        out.append([(m.get("role"), m.get("content")) for m in part])
    return out


def q_events(q, run, adds_hint=None):
    """Add events for one question, in run order. adds_hint = artifact add_calls."""
    evs = []
    si = 0
    for sess in q["haystack_sessions"]:
        parts = parts_of(sess)
        for ci, msgs in enumerate(parts):
            evs.append({"run": run, "q_id": q["question_id"], "sess": si,
                       "chunk": ci, "msgs": msgs})
        si += 1
    if adds_hint is not None and adds_hint != len(evs):
        evs[0].setdefault("notes", []).append(
            f"add_calls mismatch artifact={adds_hint} formula={len(evs)}")
    return evs


def artifact_rows(name):
    d = json.loads((OUT / name).read_text())
    return d["results"]


# Run registry: chronological add-event builders + history windows (UTC).
# Windows from the live history ADD timeline (segments) crossed with artifact
# provenance dates (see h5_guard_verification_note.md / forensics json).
REGISTRY = [
    dict(name="n5_1", scope="user_id=u_pilot", kind="artifact",
         artifact="pilot_n5.json", t0="2026-10-16T23:02:20", t1="2026-10-16T23:16:27"),
    dict(name="n5ev", scope="user_id=u_pilot", kind="artifact",
         artifact="pilot_evidence_n5.json", t0="2026-10-16T23:16:27", t1="2026-10-16T23:28:13"),
    dict(name="n50_first50", scope="user_id=u_pilot", kind="artifact",
         artifact="pilot_evidence_n50.json", t0="2026-10-16T23:28:13", t1="2026-10-17T00:24:30"),
    dict(name="n50_stratified", scope="user_id=u_pilot", kind="artifact",
         artifact="pilot_evidence_n50_stratified.json", t0="2026-10-17T06:48:13", t1="2026-10-17T07:36:13"),
    dict(name="full500", scope="user_id=u_pilot", kind="artifact",
         artifact="pilot_evidence_n500.json", t0="2026-10-17T09:57:37", t1="2026-10-17T17:22:30"),
    dict(name="b1_oldcfg", scope="user_id=u_pilot", kind="singles",
         t0="2026-10-17T18:41:28", t1="2026-10-17T19:48:29"),
    dict(name="b2_fixcfg", scope="user_id=u_pilot", kind="singles",
         t0="2026-10-17T19:48:29", t1="2026-10-17T20:54:47"),
    dict(name="pre_b6_test", scope="user_id=u_pilot", kind="placeholder",
         t0="2026-10-20T18:18:29", t1="2026-10-20T18:18:30", n_facts=12),
    dict(name="b6", scope="user_id=u_pilot", kind="singles",
         t0="2026-10-20T18:28:55", t1="2026-10-20T19:42:29"),
    dict(name="b3_probe", scope="user_id=u_pilot", kind="probe13",
         t0="2026-10-24T08:33:23", t1="2026-10-24T08:39:24"),
    dict(name="b4", scope="user_id=u_pilot", kind="singles",
         t0="2026-10-24T08:39:24", t1="2026-10-24T10:03:36"),
    dict(name="g1", scope="user_id=u_pilot", kind="singles",
         t0="2026-10-24T10:42:44", t1="2026-10-24T11:41:33"),
    dict(name="g1_probes", scope="user_id=u_probe", kind="g1probes",
         t0="2026-10-24T12:08:59", t1="2026-10-24T12:14:31"),
    dict(name="reppenalty", scope="user_id=u_probe", kind="reppenalty",
         t0="2026-10-24T13:02:52", t1="2026-10-24T13:08:55"),
    dict(name="ii", scope="user_id=u_pilot", kind="singles",
         t0="2026-10-24T13:40:55", t1="2026-10-24T14:46:44"),
    dict(name="smoke_v1", scope="user_id=u_pilot", kind="n5pick",
         t0="2026-10-24T15:30:38", t1="2026-10-24T15:36:20"),
    dict(name="smoke_v2", scope="user_id=u_pilot", kind="n5pick",
         t0="2026-10-24T15:36:20", t1="2026-10-24T15:42:00"),
    dict(name="smoke_v3", scope="user_id=u_pilot", kind="n5pick",
         t0="2026-10-24T15:42:00", t1="2026-10-24T15:47:41"),
]


def build_events(data, singles, n5pick, lookup):
    events = []  # chronological add events across all runs
    run_qadds = {}  # run -> ordered [(q_id, n_adds)]
    for reg in REGISTRY:
        evs, qa = [], []
        k = reg["kind"]
        if k == "singles":
            for q in singles:
                evs += q_events(q, reg["name"])
                qa.append((q["question_id"], 1))
        elif k == "artifact":
            rows = artifact_rows(reg["artifact"])
            for r in rows:
                q = lookup[r["q_id"]]
                e = q_events(q, reg["name"], adds_hint=r.get("add_calls"))
                evs += e
                qa.append((q["question_id"], len(e)))
        elif k == "n5pick":
            for q in n5pick:
                evs += q_events(q, reg["name"])
                qa.append((q["question_id"], 0))  # filled below
                qa[-1] = (q["question_id"],
                          sum(1 for e in evs if e["q_id"] == q["question_id"]))
        elif k == "probe13":
            for r in artifact_rows("b3_probe_lock4.json"):
                q = lookup[r["q_id"]]
                evs += q_events(q, reg["name"])
                qa.append((q["question_id"], 1))
        elif k == "placeholder":
            msgs = [("user", f"[pre-b6 test message {i} (content unrecoverable: "
                            f"evicted by the 10-row cap)]")
                    for i in range(reg["n_facts"])]
            evs.append({"run": reg["name"], "q_id": "PRE_B6_TEST", "sess": 0,
                        "chunk": 0, "msgs": msgs,
                        "notes": ["scope-uncertain: u_pilot|u_calib|u_probe "
                                  "(branches merge right after its eviction)"]})
            qa.append(("PRE_B6_TEST", 1))
        elif k == "g1probes":
            for qid8 in ("8cf51dda", "4fd1909e"):  # probe A: 1 add each
                q = lookup[qid8]
                evs += q_events(q, reg["name"])
                qa.append((q["question_id"], 1))
            for qid8 in ("8cf51dda", "cc539528", "e3fc4d6e", "4fd1909e"):  # B: 2
                q = lookup[qid8]
                sess = q["haystack_sessions"][0]
                half = len(sess) // 2
                for pi, part in enumerate((sess[:half], sess[half:])):
                    if not part:
                        continue
                    evs.append({"run": reg["name"], "q_id": q["question_id"],
                                "sess": 0, "chunk": pi,
                                "msgs": [(m.get("role"), m.get("content")) for m in part]})
                qa.append((q["question_id"], 2))
        elif k == "reppenalty":
            for r in artifact_rows("reppenalty_probe.json"):
                q = lookup[r["q_id8"]]
                evs += q_events(q, reg["name"])
                qa.append((q["question_id"], 1))
        run_qadds[reg["name"]] = qa
        for e in evs:
            events.append(dict(e, scope=reg["scope"]))
    return events, run_qadds


# ---------------------------------------------------------------------------
# 1a: exact replay of the messages table (storage.py SQL verbatim)

DDL = """CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY, session_scope TEXT, role TEXT, content TEXT,
    name TEXT, created_at DATETIME)"""
EVICT_SQL = """
    DELETE FROM messages WHERE session_scope = ? AND id NOT IN (
        SELECT id FROM (
            SELECT id FROM messages WHERE session_scope = ? ORDER BY created_at DESC LIMIT 10
        )
    )"""
LAST_SQL = """
    SELECT id, role, content, created_at FROM (
        SELECT id, role, content, created_at FROM messages
        WHERE session_scope = ? ORDER BY created_at DESC LIMIT ?
    ) ORDER BY created_at ASC"""


def replay(events):
    con = sqlite3.connect(":memory:")
    con.execute(DDL)
    row_src = {}  # id -> (run, q_id)
    per_add, ts = [], 0
    for e in events:
        ts += 1
        now = f"1970-01-01T{ts // 3600:02d}:{(ts // 60) % 60:02d}:{ts % 60:02d}"
        cur = con.execute(LAST_SQL, (e["scope"], 10)).fetchall()
        tail_srcs = [row_src.get(r[0]) for r in cur]
        # classify by the newest row's source (rows of the last save share created_at)
        primary = tail_srcs[-1] if tail_srcs else None
        if not cur:
            cls = "EMPTY"
        elif primary and primary[1] == e["q_id"] and primary[0] == e["run"]:
            cls = "SAME_Q"
        elif primary and primary[0] == e["run"]:
            cls = "CROSS_Q"
        else:
            cls = "CROSS_RUN"
        mixed = len({tuple(s) for s in tail_srcs}) > 1
        per_add.append({
            "run": e["run"], "q_id": e["q_id"], "scope": e["scope"],
            "class": cls, "tail_rows": len(cur), "tail_source": primary,
            "tail_mixed": mixed, "tail_preview": [
                (r[1], (r[2] or "")[:70]) for r in cur[:2]],
            "n_msgs_saved": len(e["msgs"]), "notes": e.get("notes", []),
        })
        # save_messages + eviction (storage.py verbatim)
        con.execute("BEGIN")
        ids = []
        for role, content in e["msgs"]:
            mid = str(uuid.uuid4())
            ids.append(mid)
            row_src[mid] = (e["run"], e["q_id"])
            con.execute("INSERT INTO messages VALUES (?,?,?,?,?,?)",
                        (mid, e["scope"], role, content, None, now))
        con.execute(EVICT_SQL, (e["scope"], e["scope"]))
        con.execute("COMMIT")
    residues = {}
    for scope in ("user_id=u_pilot", "user_id=u_probe"):
        rows = con.execute("SELECT role, content FROM messages WHERE session_scope=?",
                           (scope,)).fetchall()
        residues[scope] = sorted((r, c or "") for r, c in rows)
    con.close()
    return per_add, residues


def live_residues():
    con = sqlite3.connect(f"file:{LIVE_DB}?mode=ro&immutable=1", uri=True)
    out = {}
    for scope in ("user_id=u_pilot", "user_id=u_probe"):
        rows = con.execute("SELECT role, content FROM messages WHERE session_scope=?",
                           (scope,)).fetchall()
        out[scope] = sorted((r, c or "") for r, c in rows)
    con.close()
    return out


# ---------------------------------------------------------------------------
# history ADD facts per (run, q) via time clustering


def history_facts(run_qadds, lookup):
    con = sqlite3.connect(f"file:{LIVE_DB}?mode=ro&immutable=1", uri=True)
    rows = con.execute(
        "SELECT new_memory, created_at FROM history WHERE event='ADD' "
        "ORDER BY created_at").fetchall()
    con.close()
    parsed = [(t, datetime.fromisoformat(c)) for t, c in rows if t]
    out, warnings = {}, []
    for reg in REGISTRY:
        t0 = datetime.fromisoformat(reg["t0"] + "+00:00")
        t1 = datetime.fromisoformat(reg["t1"] + "+00:00")
        seg = [(t, c) for t, c in parsed if t0 <= c <= t1]
        if not seg:
            warnings.append(f"{reg['name']}: no history rows in window")
            continue
        clusters, prev, cur = [], None, []
        for t, c in seg:
            if prev is not None and (c - prev).total_seconds() > 10:
                clusters.append(cur)
                cur = []
            cur.append(t)
            prev = c
        if cur:
            clusters.append(cur)
        qa = run_qadds[reg["name"]]
        n_adds = sum(n for _, n in qa)
        if len(clusters) != n_adds:
            warnings.append(f"{reg['name']}: clusters {len(clusters)} != adds {n_adds}")
        # monotone DP alignment: cluster i -> question j (non-decreasing),
        # scored by unique-shingle own-matches. Robust to cluster merges/splits
        # that break naive order assignment (the first version of this script
        # shifted facts across questions and produced phantom leaks).
        facts = align_clusters(clusters, qa, UNIQ)
        out[reg["name"]] = facts
    return out, warnings


def align_clusters(clusters, qa, uniq):
    """Monotone assignment of fact-clusters to run questions by content."""
    n_q = len(qa)
    if not clusters:
        return {}

    def score(ci, qid):
        hits = 0
        for t in clusters[ci]:
            words = WORD.findall(t.lower())
            for i in range(len(words) - 4):
                g = " ".join(words[i:i + 5])
                src = uniq.get(g)
                if src and src[0] == qid:
                    hits += 1
                    break
        return hits

    NEG = -1e9
    m = len(clusters)
    dp = [[NEG] * n_q for _ in range(m)]
    arg = [[None] * n_q for _ in range(m)]
    # prefix-max transitions: a cluster may sit at any question j >= the
    # previous cluster's question (skips allowed for empty-extraction
    # questions that produced no history rows at all).
    def relax(ci, j, val, from_j):
        if val > dp[ci][j]:
            dp[ci][j] = val
            arg[ci][j] = from_j
    for j in range(n_q):
        relax(0, j, score(0, qa[j][0]), None)
    for ci in range(1, m):
        runmax, runarg = NEG, None
        for j in range(n_q):
            # running prefix max over dp[ci-1][0..j]
            if dp[ci - 1][j] > runmax:
                runmax, runarg = dp[ci - 1][j], j
            if runmax > NEG / 2:
                relax(ci, j, runmax + score(ci, qa[j][0]), runarg)
    j = max(range(n_q), key=lambda x: dp[m - 1][x])
    assign = [None] * m
    for ci in range(m - 1, -1, -1):
        assign[ci] = j
        pj = arg[ci][j]
        if pj is None:
            break
        j = pj
    facts = defaultdict(list)
    for ci, jj in enumerate(assign):
        if jj is not None:
            facts[qa[jj][0]] += clusters[ci]
    return dict(facts)


# ---------------------------------------------------------------------------
# store facts (copies) + artifact texts


def store_facts(order_map):
    """order_map: run -> {q_dir_name: full q_id} (from each run's question order)."""
    sys.path.insert(0, "/home/aleksandr/Projects/mem0-pilot-venv/lib/python3.12/site-packages")
    from qdrant_client import QdrantClient
    out, errors = {}, []
    if WORK.exists():
        shutil.rmtree(WORK)
    WORK.mkdir(parents=True)
    for run, src in STORE_DIRS.items():
        srcp, dstp = Path(src), WORK / run
        if not srcp.is_dir():
            errors.append(f"{run}: store dir missing {src}")
            continue
        shutil.copytree(srcp, dstp)
        per_q = {}
        for qdir in sorted(dstp.glob("q*")):
            if not qdir.is_dir():
                continue
            qid = order_map.get(run, {}).get(qdir.name)
            if qid is None:
                errors.append(f"{run}/{qdir.name}: no order mapping")
                continue
            try:
                cli = QdrantClient(path=str(qdir))
                colls = [c.name for c in cli.get_collections().collections]
                texts = []
                for coll in colls:
                    off = None
                    while True:
                        pts, off = cli.scroll(collection_name=coll, limit=512,
                                              offset=off, with_payload=True)
                        for p in pts:
                            pl = p.payload or {}
                            t = pl.get("data") or pl.get("text") or ""
                            if t:
                                texts.append(t)
                        if off is None:
                            break
                cli.close()
                per_q[qid] = texts
            except Exception as ex:
                errors.append(f"{run}/{qdir.name}: {ex}")
        out[run] = per_q
    return out, errors


def artifact_texts():
    """Committed artifact texts: reppenalty (texts per tag), n5-family top5."""
    out = {}
    rp = json.loads((OUT / "reppenalty_probe.json").read_text())
    per_q = defaultdict(list)
    for r in rp["results"]:
        for t in r.get("texts", []):
            per_q[r["q_id8"]].append(t)
    out["reppenalty"] = dict(per_q)
    for name, art in (("n5ev", "pilot_evidence_n5.json"),
                      ("n50_first50", "pilot_evidence_n50.json"),
                      ("n50_stratified", "pilot_evidence_n50_stratified.json"),
                      ("full500", "pilot_evidence_n500.json")):
        d = json.loads((OUT / art).read_text())
        per_q = {}
        for r in d["results"]:
            per_q[r["q_id"]] = [t.get("text", "") for t in r.get("top5", [])
                                if isinstance(t, dict) and t.get("text")]
        out[name] = per_q
    return out


# ---------------------------------------------------------------------------
# 1b: unique-shingle attribution

WORD = re.compile(r"[a-z0-9]+")


def shingle_map(data):
    uniq, shared = {}, set()
    for q in data:
        grams = set()
        for sess in q["haystack_sessions"]:
            words = []
            for m in sess:
                words += WORD.findall(str(m.get("content", "")).lower())
            for i in range(len(words) - 4):
                grams.add(" ".join(words[i:i + 5]))
        for g in grams:
            if g in uniq and uniq[g][0] != q["question_id"]:
                shared.add(g)
            else:
                uniq[g] = (q["question_id"], g)
    for g in shared:
        uniq.pop(g, None)
    return uniq


def scan_texts(texts_by_q, uniq, qid_of=None):
    """texts_by_q: {q_id: [fact texts]}; returns leak stats."""
    res = {}
    for q, texts in texts_by_q.items():
        qfull = qid_of(q) if qid_of else q
        stats = dict(n_facts=len(texts), confirmed=[], weak=[], clean=0,
                     unattr=0)
        for t in texts:
            words = WORD.findall(t.lower())
            hits = Counter()
            examples = {}
            for i in range(len(words) - 4):
                g = " ".join(words[i:i + 5])
                src = uniq.get(g)
                if src and src[0] != qfull:
                    hits[src[0]] += 1
                    examples.setdefault(src[0], []).append(g)
            if not hits:
                stats["clean" if words else "unattr"] += 1
            elif max(hits.values()) >= 2:
                top = max(hits, key=hits.get)
                stats["confirmed"].append({"text": t[:140],
                                           "foreign_q": top,
                                           "n_shingles": hits[top],
                                           "example": examples[top][0]})
            else:
                top = next(iter(hits))
                stats["weak"].append({"text": t[:140], "foreign_q": top,
                                      "n_shingles": 1,
                                      "example": examples[top][0]})
        res[q] = stats
    return res


def main():
    t_start = time.time()
    global UNIQ
    data, singles, n5pick = load_dataset()
    lookup = q_lookup(data)
    events, run_qadds = build_events(data, singles, n5pick, lookup)
    print(f"[1] events built: {len(events)} add calls across {len(REGISTRY)} runs")

    per_add, residues = replay(events)
    live = live_residues()
    validation = {}
    for scope in ("user_id=u_pilot", "user_id=u_probe"):
        validation[scope] = {
            "replay_equals_live": residues[scope] == live[scope],
            "replay_n": len(residues[scope]), "live_n": len(live[scope]),
        }
    print(f"[2] replay done; residue validation: "
          f"{ {k.split('=')[1]: v['replay_equals_live'] for k, v in validation.items()} }")

    by_run = defaultdict(lambda: Counter())
    examples = defaultdict(list)
    for a in per_add:
        by_run[a["run"]][a["class"]] += 1
        if a["class"] in ("CROSS_Q", "CROSS_RUN") and len(examples[a["run"]]) < 3:
            examples[a["run"]].append(a)

    print("[3] shingle index (needed for DP alignment)...")
    UNIQ = shingle_map(data)
    print(f"    unique shingles: {len(UNIQ)}")

    print("[4] history clustering + DP alignment...")
    hist, warnings = history_facts(run_qadds, lookup)

    order_map = {
        "b4": {f"q{i}": q["question_id"] for i, q in enumerate(singles)},
        "g1": {f"q{i}": q["question_id"] for i, q in enumerate(singles)},
        "ii": {f"q{i}": q["question_id"] for i, q in enumerate(singles)},
        "b3probe": {f"q{i}": lookup[r["q_id"]]["question_id"]
                    for i, r in enumerate(artifact_rows("b3_probe_lock4.json"))},
        "g1probes": {"qa0": lookup["8cf51dda"]["question_id"],
                     "qa1": lookup["4fd1909e"]["question_id"],
                     "qb0": lookup["8cf51dda"]["question_id"],
                     "qb1": lookup["cc539528"]["question_id"],
                     "qb2": lookup["e3fc4d6e"]["question_id"],
                     "qb3": lookup["4fd1909e"]["question_id"]},
    }
    print("[5] reading store copies...")
    stores, store_errors = store_facts(order_map)
    print(f"    store errors: {store_errors or 'none'}")

    print("[6] artifact texts...")
    arts = artifact_texts()

    qid_full = lambda s: lookup[s]["question_id"] if s in lookup else s

    leak = {}
    for run in ("b1_oldcfg", "b2_fixcfg", "b6", "b3_probe", "b4", "g1", "ii",
                "smoke_v1", "smoke_v2", "smoke_v3", "n5_1", "n5ev",
                "n50_first50", "n50_stratified", "full500"):
        src = {}
        if run in hist:
            src["history_adds"] = scan_texts(hist[run], UNIQ, qid_full)
        if run in stores:
            src["store"] = scan_texts(stores[run], UNIQ, qid_full)
        if run in arts:
            src["artifact_top5_or_texts"] = scan_texts(arts[run], UNIQ, qid_full)
        leak[run] = src

    # cross-validation of attribution: for runs with BOTH store and history
    # channels, per-question overlap of fact text sets should be near-total.
    xval = {}
    for run in ("b4", "g1", "ii", "b3_probe"):
        if run in stores and run in hist:
            agree_q, tot_q, agree_f, tot_f = 0, 0, 0, 0
            for qid, stexts in stores[run].items():
                htexts = set(hist[run].get(qid, []))
                tot_q += 1
                if stexts and set(stexts) & htexts:
                    agree_q += 1
                tot_f += len(stexts)
                agree_f += sum(1 for t in stexts if t in htexts)
            xval[run] = {"questions_with_overlap": agree_q, "questions": tot_q,
                         "facts_in_history": agree_f, "facts_in_store": tot_f}

    # predecessor-directed check: facts of q carrying unique shingles of the
    # structural predecessor (the add-walk's CROSS_Q/CROSS_RUN tail source)
    pred_hits = defaultdict(lambda: {"runs": 0, "facts": 0})
    for run, srcs in leak.items():
        seen_pred = False
        for src_name, per_q in srcs.items():
            for q, st in per_q.items():
                preds = {a["tail_source"][1] for a in per_add
                         if a["run"] == run and a["q_id"] == q
                         and a["class"] in ("CROSS_Q", "CROSS_RUN")}
                for lst in (st["confirmed"], st["weak"]):
                    if any(x["foreign_q"] in preds for x in lst):
                        seen_pred = True
                        pred_hits[run + "/" + src_name]["facts"] += sum(
                            1 for x in lst if x["foreign_q"] in preds)
        if seen_pred:
            pred_hits[run]["runs"] = 1

    out = {
        "meta": {
            "date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "evidence": "~/.mem0/history.db opened mode=ro&immutable=1 only",
            "mechanism": "V3 pipeline: get_last_messages (main.py:922) -> "
                         "'## Last k Messages' (prompts.py:1037); save_messages "
                         "evicts to last-10 rows per scope (storage.py)",
            "eviction_note": "raw messages beyond each scope's final 10-row "
                             "residue were evicted in flight; the live db keeps "
                             "only residues (u_pilot = last Oct-24 smoke session)",
            "replay_validation": validation,
            "cluster_warnings": warnings,
            "store_errors": store_errors,
            "store_vs_history_attribution": xval,
        },
        "part_1a": {
            "total_add_calls": len(events),
            "by_run": {r: dict(c) for r, c in by_run.items()},
            "examples": {r: v for r, v in examples.items()},
        },
        "part_1b": leak,
        "predecessor_directed": {k: dict(v) for k, v in pred_hits.items()},
    }
    (OUT / "history_confound_forensics.json").write_text(
        json.dumps(out, indent=1, ensure_ascii=False))
    print(f"[done] wrote json ({time.time() - t_start:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
