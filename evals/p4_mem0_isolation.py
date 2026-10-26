#!/usr/bin/env python3
"""P4: behavioral cross-subject isolation test for mem0@0724291b
(proposals/p4-mem0-behavioral-isolation.md v0.2 -- NOT RUN before owner
sanction; this file is the implementation draft committed for review).

One file, CPU-only, seconds: embeds a deterministic stub embedder+LLM server
(http thread), wires stock mem0 to it (infer=False -- no generation), and
runs, per scope key (user_id / agent_id / run_id):
  - main: 3 marker-disjoint subjects, alternating writes, cross reads
    (search / get_all / history SQL) -- zero foreign expected;
  - hostile queries: query text == a foreign fact -- foreign=0 AND
    own_recall>0 (filter applied BEFORE top-k);
controls (both must fire; an exception in a control is NOT a pass:
  {"raised": "<type>", fired=false} -> passed=false with the
  'control inconclusive' note):
  - shared-id (detector sanity);
  - POST-TOP-K-FILTER mutation (third control): vector_store.search
    wrapped so the scope filter applies AFTER top-k; the hostile query
    must yield own_recall=0 under the mutation and >0 unmutated;
  - MUTATIONAL at the VECTOR-STORE level: the instance's vector_store.search
    and vector_store.list are wrapped so the scope key drops out of the
    filter AFTER Memory's input validation (Memory.search/get_all are called
    normally WITH the key; the wrapper strips the key at the store boundary,
    simulating a store-layer filter-loss bug); the main scenario must go red
    via leaks (search AND get_all paths), never via an exception;
incident demo (NOT a mem0 verdict): one user, shared history db -- the tail
channel shown; plus the run_id measurement (does a per-question run_id
isolate the tail natively?);
observed behavior (outside the verdict): get/update/delete by a foreign
record id -- facts only, no defect conclusion.

Report: results/p4_mem0_isolation_report.json (+ CONFIG_SHA256 announce).
"""
import hashlib
import json
import os
import random
import sqlite3
import sys
import threading
import time
import urllib.request
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from config_fingerprint import announce

# H5 hygiene: mem0's defaults (history db AND the qdrant migrations lock
# folder) live under ~/.mem0 -- this test redirects the whole mem0_dir into a
# temp dir BEFORE mem0 is imported (mem0 reads MEM0_DIR at import/config
# time). Without this, concurrent per-scenario qdrant-local instances fight
# over the LIVE ~/.mem0/migrations_qdrant lock (observed: RuntimeError on
# the second scenario; the live dir was verified untouched -- the lock check
# fires before any write).
_MEM0_TMP = Path("/tmp/opencode") / f"p4_mem0dir_{int(time.time())}"
(_MEM0_TMP / "migrations_qdrant").mkdir(parents=True, exist_ok=True)
os.environ["MEM0_DIR"] = str(_MEM0_TMP)
# Oct-17 lesson: with telemetry ON, every Memory opens a second QdrantLocal
# (the 'mem0migrations' store, mem0/memory/main.py:534) under
# <mem0_dir>/migrations_qdrant -> the shared folder lock breaks the second
# Memory instance. OFF = no migrations store at all.
os.environ.setdefault("MEM0_TELEMETRY", "False")


def _close(m):
    try:
        m.vector_store.client.close()
    except Exception:
        pass

OUT = Path(__file__).resolve().parent / "results"
DIMS = 768
KEYS = ("user_id", "agent_id", "run_id")
FACTS_PER = 6

FACT_SETS = {
    "user_id": {
        "A": [f"user record: shared fact {i} of subject A: marker-UA{i} likes teal-{i} stones" for i in range(FACTS_PER)],
        "B": [f"user record: shared fact {i} of subject B: marker-UB{i} prefers amber-{i} river" for i in range(FACTS_PER)],
        "C": [f"user record: shared fact {i} of subject C: marker-UC{i} collects cobalt-{i} glass" for i in range(FACTS_PER)],
    },
    "agent_id": {
        "A": [f"user record: shared fact {i} of subject A: marker-GA{i} drives crimson-{i} coupe" for i in range(FACTS_PER)],
        "B": [f"user record: shared fact {i} of subject B: marker-GB{i} paints indigo-{i} murals" for i in range(FACTS_PER)],
        "C": [f"user record: shared fact {i} of subject C: marker-GC{i} bakes lemon-{i} cakes" for i in range(FACTS_PER)],
    },
    "run_id": {
        "A": [f"user record: shared fact {i} of subject A: marker-RA{i} plays olive-{i} guitars" for i in range(FACTS_PER)],
        "B": [f"user record: shared fact {i} of subject B: marker-RB{i} studies jade-{i} minerals" for i in range(FACTS_PER)],
        "C": [f"user record: shared fact {i} of subject C: marker-RC{i} sails copper-{i} boats" for i in range(FACTS_PER)],
    },
}


# token-compositional deterministic embedding: each token hashes to a fixed
# random vector; text embedding = normalized sum of token vectors. Same text
# -> same vector (cosine 1.0); texts SHARING TOKENS get positive cosine
# (~shared/total) -- required so the hostile-query own_recall expectation is
# satisfiable (a foreign-fact query still recalls the user's own structurally
# similar facts above the 0.1 similarity threshold); a pure full-text hash
# makes different texts orthogonal and the expectation vacuously fails.
_TOK_VEC = {}


def _vec(text):
    import math as _math
    toks = [t for t in text.strip().lower().split() if t]
    if not toks:
        toks = ["<empty>"]
    v = [0.0] * DIMS
    for t in toks:
        if t not in _TOK_VEC:
            seed = int(hashlib.sha256(("tok:" + t).encode()).hexdigest()[:16], 16)
            # ONE Random per token (a fresh Random(seed) PER ELEMENT yields the
            # same first sample every time -> every token vector becomes a
            # constant [x,x,...] direction -> all texts end up parallel +-1;
            # that root bug produced the erratic own_recall earlier). Proper
            # per-token directions give: shared-k-of-(m,n) cos ~ k/sqrt(mn)
            # (7 of 12 -> ~0.58 > the 0.1 threshold for hostile own_recall);
            # near-copy (12 of 14) ~ 0.9 >> different-fact ~0.58 (postfilter
            # starvation ranking); identical texts 1.0 (mutation probes).
            rng = random.Random(seed)
            _TOK_VEC[t] = [rng.uniform(-1, 1) for _ in range(DIMS)]
        tv = _TOK_VEC[t]
        v = [a + b for a, b in zip(v, tv)]
    n = _math.sqrt(sum(x * x for x in v)) or 1.0
    return [round(x / n, 6) for x in v]


class StubHandler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence
        pass

    def _json(self, code, obj):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        n = int(self.headers.get("Content-Length") or 0)
        req = json.loads(self.rfile.read(n) or b"{}")
        if self.path.endswith("/v1/embeddings"):
            inp = req.get("input")
            texts = inp if isinstance(inp, list) else [inp]
            self._json(200, {"object": "list", "model": req.get("model", "stub"),
                             "data": [{"object": "embedding", "index": i,
                                       "embedding": _vec(str(t))} for i, t in enumerate(texts)]})
        elif self.path.endswith("/v1/chat/completions"):
            self._json(200, {"id": "stub", "object": "chat.completion",
                             "choices": [{"index": 0, "finish_reason": "stop",
                                          "message": {"role": "assistant",
                                                      "content": '{"memory": []}'}}]})
        else:
            self._json(404, {"error": "not found"})


def start_stub():
    srv = HTTPServer(("127.0.0.1", 0), StubHandler)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    return srv, f"http://127.0.0.1:{srv.server_address[1]}/v1"


def mem_cfg(stub_url, store_dir, hist_db):
    return {
        "llm": {"provider": "openai", "config": {
            "model": "stub-llm", "temperature": 0, "max_tokens": 32,
            "openai_base_url": stub_url, "api_key": "stub"}},
        "embedder": {"provider": "openai", "config": {
            "model": "stub-embedder", "openai_base_url": stub_url,
            "api_key": "stub", "embedding_dims": DIMS}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": "p4", "embedding_model_dims": DIMS,
            "path": store_dir}},
        "history_db_path": hist_db,
        "version": "v1.1",
    }


def markers_of(key, subject):
    """Markers EXTRACTED from the fact texts (not from a naming convention:
    the first full run failed because the convention generated marker-AA*
    for agent_id while the facts contain marker-GA* -- the detector was
    blind for that key; harness bug, fixed by extraction)."""
    import re as _re
    return _re.findall(r"marker-\S+", " ".join(FACT_SETS[key][subject]))


def foreign_in(key, text, own):
    for s in "ABC":
        if s == own:
            continue
        for m in markers_of(key, s):
            if m in text:
                return s
    return None


def history_rows(hist_db):
    con = sqlite3.connect(f"file:{hist_db}?mode=ro&immutable=1", uri=True)
    rows = con.execute("SELECT session_scope, role, content FROM messages").fetchall()
    con.close()
    return rows


def run_key_scenario(mem_cls, stub_url, root, key, facts, filters_of):
    """Main + hostile for one scope key on fresh stores. Storage channels
    (search/get_all/hostile) run at infer=False. The MESSAGES channel runs
    as a second pass with infer=True against the deterministic STUB chat
    (returns '{"memory": []}'): mem0 only writes messages via save_messages
    in the extraction pipeline -- at infer=False the messages table stays
    empty and the channel check would be vacuous (first-run finding)."""
    store = root / f"{key}/store"
    hist = str(root / f"{key}/history.db")
    m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
    order = []
    for i in range(FACTS_PER):
        for s in "ABC":
            order.append((s, facts[s][i]))
    for s, text in order:
        kw = {key: s}
        m.add([{"role": "user", "content": text}], infer=False, **kw)
    res = {"search_leaks": {}, "get_all_leaks": {}, "history_leaks": {},
           "hostile": {}, "own_counts": {}}
    for s in "ABC":
        flt = {key: s}
        got = m.get_all(filters=flt)
        items = got.get("results", got) if isinstance(got, dict) else got
        texts = [it.get("memory", "") for it in items]
        res["get_all_leaks"][s] = sum(1 for t in texts if foreign_in(key, t, s))
        res["own_counts"][s] = len(texts)  # non-vacuousness diagnostic
        hits = 0
        for probe in facts[s][:3]:
            r = m.search(probe, filters=flt, top_k=5)
            rr = r.get("results", r) if isinstance(r, dict) else r
            hits += sum(1 for it in rr if foreign_in(key, it.get("memory", ""), s))
        res["search_leaks"][s] = hits
    # hostile: query == foreign fact text, under each subject
    for s in "ABC":
        other = "B" if s == "A" else "A"
        q = facts[other][0]
        r = m.search(q, filters={key: s}, top_k=5)
        rr = r.get("results", r) if isinstance(r, dict) else r
        texts = [it.get("memory", "") for it in rr]
        res["hostile"][s] = {
            "foreign_count": sum(1 for t in texts if foreign_in(key, t, s)),
            "own_recall": sum(1 for t in texts if not foreign_in(key, t, s)
                              and any(mk in t for mk in markers_of(key, s))),
        }
    _close(m)
    # messages channel: infer=True on the stub chat (deterministic, no real LLM)
    store2 = root / f"{key}/store_msg"
    hist2 = str(root / f"{key}/history_msg.db")
    m2 = mem_cls.from_config(mem_cfg(stub_url, str(store2), hist2))
    for i in range(3):
        for s in "ABC":
            m2.add([{"role": "user", "content": facts[s][i]}], infer=True, **{key: s})
    rows = history_rows(hist2)
    for s in "ABC":
        res["history_leaks"][s] = sum(
            1 for sc, _, c in rows
            if f"{key}={s}" in sc and foreign_in(key, c or "", s))
    res["history_msg_rows_total"] = len(rows)  # non-vacuousness diagnostic
    _close(m2)
    return res


def run_mutation_control(mem_cls, stub_url, root, key, facts):
    """(b) MUTATIONAL at the VECTOR-STORE level: wrap the instance's
    vector_store.search / vector_store.list so the scope key drops from the
    filter AFTER Memory's input validation (Memory.search/get_all are called
    normally WITH the key; verified against pin 0724291b paths:
    Memory.search -> _search_vector_store -> vector_store.search(...);
    Memory.get_all -> vector_store.list(filters, top_k)). NOTE: search has a
    similarity threshold (0.1 default) -- with the hash-stub embedder only
    near-identical texts pass it, so the mutated search scenario plants
    OVERLAPPING fact texts (same stem + subject marker): a foreign near-copy
    passes the threshold and MUST appear in the mutated (unfiltered) results;
    the un-mutated main store never sees it because the texts differ. The
    control MUST go red via leaks, never via an exception (an exception ->
    raised/inconclusive)."""
    try:
        store = root / f"mut_{key}/store"
        hist = str(root / f"mut_{key}/history.db")
        m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
        # ordinary disjoint facts for subject A (to have own items)
        for i in range(3):
            m.add([{"role": "user", "content": facts["A"][i]}], infer=False, **{key: "A"})
        # OVERLAPPING near-copies: B's facts are near-identical to A's queries
        for i in range(3):
            m.add([{"role": "user", "content":
                    f"{facts['A'][i]} (variant {markers_of(key, 'B')[i]})"}],
                  infer=False, **{key: "B"})
        vs = m.vector_store
        orig_search, orig_list = vs.search, vs.list

        def strip(f):
            return {k: v for k, v in (f or {}).items() if k != key}

        vs.search = lambda query, vectors, top_k=5, filters=None, **kw: \
            orig_search(query, vectors, top_k=top_k, filters=strip(filters), **kw)
        vs.list = lambda filters=None, top_k=100, **kw: \
            orig_list(filters=strip(filters), top_k=top_k, **kw)
        try:
            search_leaks = get_all_leaks = 0
            # NORMAL API calls with the key -- validation inside Memory runs
            # first; the query is the EXACT stored foreign text (the hash-stub
            # embedder gives similarity only to identical strings, and the
            # 0.1 similarity threshold must pass for the leak to surface)
            for i in range(3):
                probe = f"{facts['A'][i]} (variant {markers_of(key, 'B')[i]})"
                r = m.search(probe, filters={key: "A"}, top_k=5)
                rr = r.get("results", r) if isinstance(r, dict) else r
                search_leaks += sum(1 for it in rr
                                    if foreign_in(key, it.get("memory", ""), "A"))
            g = m.get_all(filters={key: "A"})
            gg = g.get("results", g) if isinstance(g, dict) else g
            get_all_leaks = sum(1 for it in gg
                                if foreign_in(key, it.get("memory", ""), "A"))
        finally:
            vs.search, vs.list = orig_search, orig_list
        _close(m)
        return {"leaks_search": search_leaks, "leaks_get_all": get_all_leaks,
                "fired": (search_leaks + get_all_leaks) > 0}
    except Exception as e:
        return {"raised": type(e).__name__, "detail": str(e)[:120],
                "fired": False, "inconclusive": True}


def run_shared_id_control(mem_cls, stub_url, root, key, facts):
    """(a) all subjects under ONE shared key value -> detector must fire.
    An exception -> {"raised": ...} / fired=false -> control inconclusive."""
    try:
        store = root / f"shared_{key}/store"
        hist = str(root / f"shared_{key}/history.db")
        m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
        shared = {key: "u_shared"}
        for i in range(FACTS_PER):
            for s in "ABC":
                m.add([{"role": "user", "content": facts[s][i]}], infer=False, **shared)
        flt = {key: "u_shared"}
        got = m.get_all(filters=flt)
        items = got.get("results", got) if isinstance(got, dict) else got
        texts = [it.get("memory", "") for it in items]
        leaks = sum(1 for t in texts if foreign_in(key, t, None))
        r = m.search(facts["A"][0], filters=flt, top_k=5)
        rr = r.get("results", r) if isinstance(r, dict) else r
        sleaks = sum(1 for it in rr if foreign_in(key, it.get("memory", ""), None))
        _close(m)
        return {"get_all_cross_items": leaks, "search_cross_items": sleaks,
                "fired": (leaks + sleaks) > 0}
    except Exception as e:
        return {"raised": type(e).__name__, "detail": str(e)[:120],
                "fired": False, "inconclusive": True}


def run_postfilter_control(mem_cls, stub_url, root, key, facts):
    """(c) POST-TOP-K FILTER mutation at the VECTOR-STORE level: wrap
    vector_store.search so the scope filter is applied AFTER the top-k
    selection (unfiltered top-k, then payload-filtered). The hostile query
    (verbatim foreign fact text, 5 exact foreign copies stored so the
    unfiltered top-k is fully occupied by foreign items) must yield
    own_recall == 0 under the mutation (starved empty result), while the
    UNMUTATED path on the same store must yield own_recall > 0 (the contrast
    pair proves the discriminator). An exception -> raised/inconclusive."""
    try:
        store = root / f"postf_{key}/store"
        hist = str(root / f"postf_{key}/history.db")
        m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
        # subject A: 3 own facts; subject B: 5 DISTINCT near-copies of its
        # fact[0] (base + 2 suffix tokens: cosine ~0.92 to the query, above
        # A's own ~0.6 -- mem0's hash-dedup would collapse exact duplicates,
        # so the copies differ slightly while all out-scoring A's items)
        for i in range(3):
            m.add([{"role": "user", "content": facts["A"][i]}], infer=False, **{key: "A"})
        for n in range(5):
            m.add([{"role": "user", "content": f"{facts['B'][0]} note {n}"}],
                  infer=False, **{key: "B"})
        vs = m.vector_store
        orig_search = vs.search

        def postfilter_search(query, vectors, top_k=5, filters=None, **kw):
            # naive post-filter implementation: select the USER-REQUESTED
            # top-k (5) WITHOUT the scope filter, then filter by payload.
            # NOTE: mem0's real flow asks the store for internal_limit =
            # max(4*top_k, 60) candidates -- which by itself mitigates naive
            # starvation; this control simulates the pure class (filter
            # strictly after the requested k) to prove the TEST detects it.
            raw = orig_search(query, vectors, top_k=top_k, filters=None, **kw)
            if not filters:
                return raw
            want = filters.get(key)
            out = []
            for r in raw[:5]:  # the user-requested k = 5
                pl = getattr(r, "payload", None) or {}
                if pl.get(key) == want:
                    out.append(r)
            return out

        probe = facts["B"][0]  # hostile: verbatim foreign fact
        vs.search = postfilter_search
        try:
            r = m.search(probe, filters={key: "A"}, top_k=5)
            rr = r.get("results", r) if isinstance(r, dict) else r
            texts = [it.get("memory", "") for it in rr]
            mutated_own = sum(1 for t in texts if any(mk in t for mk in markers_of(key, "A")))
        finally:
            vs.search = orig_search
        r2 = m.search(probe, filters={key: "A"}, top_k=5)
        rr2 = r2.get("results", r2) if isinstance(r2, dict) else r2
        texts2 = [it.get("memory", "") for it in rr2]
        unmutated_own = sum(1 for t in texts2 if any(mk in t for mk in markers_of(key, "A")))
        unmutated_foreign = sum(1 for t in texts2 if foreign_in(key, t, "A"))
        _close(m)
        return {"mutated_own_recall": mutated_own,
                "unmutated_own_recall": unmutated_own,
                "unmutated_foreign": unmutated_foreign,
                "fired": mutated_own == 0 and unmutated_own > 0}
    except Exception as e:
        return {"raised": type(e).__name__, "detail": str(e)[:120],
                "fired": False, "inconclusive": True}


def run_incident_demo(mem_cls, stub_url, root):
    """One user, SHARED history db -- the H5 channel; + run_id measurement.
    infer=True against the stub chat: the messages channel (save_messages)
    only runs in mem0's extraction pipeline; the stub returns an empty
    extraction deterministically -- no real LLM."""
    out = {}
    # (i) same scope, two sessions
    store = root / "demo_same/store"
    hist = str(root / "demo_same/history.db")
    m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
    sess1 = [{"role": "user", "content": f"demo s1 line {i} about kettles-{i}"} for i in range(8)]
    sess2 = [{"role": "user", "content": f"demo s2 line {i} about anchors-{i}"} for i in range(4)]
    m.add(sess1, user_id="u_demo", infer=True)  # stub chat: empty extraction,
    m.add(sess2, user_id="u_demo", infer=True)  # but save_messages WRITES (channel!)
    rows = history_rows(hist)
    demo_scope = [c for sc, _, c in rows if sc == "user_id=u_demo"]
    s1_seen = sum(1 for c in demo_scope if "kettles" in (c or ""))
    s2_seen = sum(1 for c in demo_scope if "anchors" in (c or ""))
    out["same_scope"] = {"s1_rows_in_scope": s1_seen, "s2_rows_in_scope": s2_seen,
                         "channel_shown": s1_seen > 0 and s2_seen > 0}
    # (ii) different run_id per session, SAME shared history db
    store = root / "demo_runid/store"
    hist2 = str(root / "demo_runid/history.db")
    m2 = mem_cls.from_config(mem_cfg(stub_url, str(store), hist2))
    m2.add(sess1, user_id="u_demo", run_id="q1", infer=True)
    m2.add(sess2, user_id="u_demo", run_id="q2", infer=True)
    rows2 = history_rows(hist2)
    q2_scope = [c for sc, _, c in rows2 if "run_id=q2" in sc and "user_id=u_demo" in sc]
    q1_in_q2 = sum(1 for c in q2_scope if "kettles" in (c or ""))
    q2_own = sum(1 for c in q2_scope if "anchors" in (c or ""))
    out["run_id"] = {"q2_scope_rows": len(q2_scope), "q2_own_rows": q2_own,
                     "s1_rows_leaked_into_q2": q1_in_q2,
                     "run_id_isolates_tail": q1_in_q2 == 0 and q2_own > 0}
    _close(m)
    _close(m2)
    return out


def run_observed_behavior(mem_cls, stub_url, root):
    """Facts only, no defect conclusion, outside the verdict."""
    store = root / "observed/store"
    hist = str(root / "observed/history.db")
    m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
    m.add([{"role": "user", "content": "obsA marker-OA0 secret"}], user_id="o_A", infer=False)
    m.add([{"role": "user", "content": "obsB marker-OB0 secret"}], user_id="o_B", infer=False)
    got = m.get_all(filters={"user_id": "o_B"})
    items = got.get("results", got) if isinstance(got, dict) else got
    bid = items[0].get("id") if items else None
    out = {"foreign_memory_id": bid, "get": None, "update": None, "delete": None}
    try:
        g = m.get(bid)
        out["get"] = {"returned": bool(g), "text_preview": (g.get("memory", "")[:40] if isinstance(g, dict) else str(g)[:40])}
    except Exception as e:
        out["get"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        u = m.update(bid, "obsB modified by foreign actor")
        out["update"] = {"ok": True, "raw": str(u)[:80]}
    except Exception as e:
        out["update"] = {"error": f"{type(e).__name__}: {e}"}
    try:
        d = m.delete(bid)
        out["delete"] = {"ok": True, "raw": str(d)[:80]}
        got2 = m.get_all(filters={"user_id": "o_B"})
        it2 = got2.get("results", got2) if isinstance(got2, dict) else got2
        out["delete"]["record_gone_after"] = not any(it.get("id") == bid for it in it2)
    except Exception as e:
        out["delete"] = {"error": f"{type(e).__name__}: {e}"}
    _close(m)
    return out


def dry_mutation():
    """Dry check WITHOUT a verdict report: run ONLY the mutational control
    (user_id key) and print its outcome -- it must go red via leaks (> 0),
    not via an exception (an exception = raised/inconclusive = fix first)."""
    from mem0 import Memory
    srv, stub_url = start_stub()
    root = Path("/tmp/opencode") / f"p4_dry_{int(time.time())}"
    root.mkdir(parents=True)
    try:
        out = run_mutation_control(Memory, stub_url, root, "user_id", FACT_SETS["user_id"])
    finally:
        srv.shutdown()
    print(json.dumps(out, indent=2, ensure_ascii=False))
    ok = out.get("fired") is True and "raised" not in out
    print("DRY MUTATION: " + ("RED via leaks -- OK to proceed" if ok else
                              "INCONCLUSIVE/EXCEPTION -- do not proceed"))
    return 0 if ok else 1


def stub_selfcheck():
    """Pre-check (2026-10-26, council review): the stub must give different
    documents NON-parallel vectors -- cos(different docs) must not be 1.0.
    The 02e1c4c verdict run shipped a Random-per-element bug that made every
    token vector a constant direction (all texts parallel, cosines +-1): the
    hostile/filter-order discriminator was vacuous. This gate refuses to run
    on such a degenerate stub."""
    a = _vec("alpha beta gamma delta epsilon zeta")
    b = _vec("one two three four five six")  # DISJOINT tokens: the stub is a
    # bag-of-tokens -- same tokens in reverse order are identical, not different
    c = sum(x * y for x, y in zip(a, b))
    same = _vec("alpha beta gamma delta epsilon zeta")
    self = sum(x * y for x, y in zip(a, same))
    print(f"stub selfcheck: cos(different docs)={c:.4f} cos(same)={self:.4f}",
          flush=True)
    if abs(self - 1.0) > 1e-6:
        print("DEGENERATE STUB: cos(same doc) != 1.0 -- refusing to run",
              flush=True)
        sys.exit(2)
    if abs(c - 1.0) < 1e-3:
        print("DEGENERATE STUB: different documents are parallel (cos ~ 1.0) "
              "-- refusing to run", flush=True)
        sys.exit(2)


def main():
    stub_selfcheck()  # unconditional pre-flight: refuse to run on a degenerate stub
    if len(sys.argv) > 1 and sys.argv[1] == "dry-mutation":
        return dry_mutation()
    fp = announce({"runner": "evals/p4_mem0_isolation.py",
                   "llm": {"model": "stub-llm", "infer": "False (no generation)"},
                   "embedder": "stub (sha256-seeded 768-dim, deterministic)",
                   "vector_store": "qdrant local, temp dir",
                   "history_db": "temp per scenario (H5 lesson)",
                   "mem0_version": "v1.1", "scope_keys": list(KEYS),
                   "controls": ["shared-id", "mutational", "postfilter"],
                   "channels": ["search", "get_all", "history_rows", "hostile"]},
                  "http://127.0.0.1:1/v1", label="p4")  # no live LLM server; stub below
    from mem0 import Memory
    srv, stub_url = start_stub()
    root = Path("/tmp/opencode") / f"p4_mem0_{int(time.time())}"
    root.mkdir(parents=True)
    report = {"provenance": {**fp, "mem0": "0724291b pin",
                             "date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
                             "design": "proposals/p4-mem0-behavioral-isolation.md v0.2"},
              "main": {}, "controls": {}, "incident_demo": {}, "observed_behavior": {}}
    try:
        for key in KEYS:
            flt_maker = lambda s: {key: s}
            report["main"][key] = run_key_scenario(Memory, stub_url, root, key,
                                                   FACT_SETS[key], flt_maker)
            report["controls"][f"mutation_{key}"] = run_mutation_control(
                Memory, stub_url, root, key, FACT_SETS[key])
            report["controls"][f"shared_id_{key}"] = run_shared_id_control(
                Memory, stub_url, root, key, FACT_SETS[key])
            report["controls"][f"postfilter_{key}"] = run_postfilter_control(
                Memory, stub_url, root, key, FACT_SETS[key])
        report["incident_demo"] = run_incident_demo(Memory, stub_url, root)
        report["observed_behavior"] = run_observed_behavior(Memory, stub_url, root)
    finally:
        srv.shutdown()

    def zero(x):
        return x == 0
    main_ok = all(
        zero(v) for key in KEYS
        for ch in ("search_leaks", "get_all_leaks", "history_leaks")
        for v in report["main"][key][ch].values()) and all(
        h["foreign_count"] == 0 and h["own_recall"] > 0
        for key in KEYS for h in report["main"][key]["hostile"].values())
    controls_ok = all(report["controls"][k]["fired"] for k in report["controls"])
    inconclusive = [k for k in report["controls"] if report["controls"][k].get("raised")]
    report["control_inconclusive"] = inconclusive  # any -> passed false
    report["passed"] = bool(main_ok and controls_ok and not inconclusive)
    import platform
    try:
        import subprocess
        pipmem = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                capture_output=True, text=True).stdout
        pipmem = "\n".join(l for l in pipmem.splitlines() if "mem0" in l.lower())
    except Exception:
        pipmem = "unavailable"
    report["environment"] = {"uname": " ".join(os.uname()), "python": platform.python_version(),
                             "pip_freeze_mem0": pipmem,
                             "stand": f"CPU-only, stub embedder, {platform.system()}"}
    (OUT / "p4_mem0_isolation_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    print("P4 PASSED" if report["passed"] else "P4 FAILED")
    for key in KEYS:
        print(f"  {key}: main={report['main'][key]}")
    print(f"  controls: {report['controls']}")
    print(f"  incident_demo: {report['incident_demo']}")
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    sys.exit(main())
