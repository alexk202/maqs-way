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
controls (both must fire):
  - shared-id (detector sanity);
  - MUTATIONAL: Memory.search/get_all wrapped so the scope key drops out of
    the filter construction -- the main scenario must turn red;
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

OUT = Path(__file__).resolve().parent / "results"
DIMS = 768
KEYS = ("user_id", "agent_id", "run_id")
FACTS_PER = 6

FACT_SETS = {
    "user_id": {
        "A": [f"uA fact {i}: marker-UA{i} likes teal-{i} stones" for i in range(FACTS_PER)],
        "B": [f"uB fact {i}: marker-UB{i} prefers amber-{i} river" for i in range(FACTS_PER)],
        "C": [f"uC fact {i}: marker-UC{i} collects cobalt-{i} glass" for i in range(FACTS_PER)],
    },
    "agent_id": {
        "A": [f"agA fact {i}: marker-GA{i} drives crimson-{i} coupe" for i in range(FACTS_PER)],
        "B": [f"agB fact {i}: marker-GB{i} paints indigo-{i} murals" for i in range(FACTS_PER)],
        "C": [f"agC fact {i}: marker-GC{i} bakes lemon-{i} cakes" for i in range(FACTS_PER)],
    },
    "run_id": {
        "A": [f"rnA fact {i}: marker-RA{i} plays olive-{i} guitars" for i in range(FACTS_PER)],
        "B": [f"rnB fact {i}: marker-RB{i} studies jade-{i} minerals" for i in range(FACTS_PER)],
        "C": [f"rnC fact {i}: marker-RC{i} sails copper-{i} boats" for i in range(FACTS_PER)],
    },
}


def _vec(text):
    seed = int(hashlib.sha256(text.strip().lower().encode()).hexdigest()[:16], 16)
    rng = random.Random(seed)
    return [round(rng.uniform(-1, 1), 6) for _ in range(DIMS)]


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
    return [f"marker-{key[0].upper()}{subject}{i}" for i in range(FACTS_PER)]


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
    """Main + hostile for one scope key on a fresh store."""
    store = root / f"{key}/store"
    hist = str(root / f"{key}/history.db")
    m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
    # alternating writes
    order = []
    for i in range(FACTS_PER):
        for s in "ABC":
            order.append((s, facts[s][i]))
    for s, text in order:
        kw = {key: s}
        m.add([{"role": "user", "content": text}], infer=False, **kw)
    res = {"search_leaks": {}, "get_all_leaks": {}, "history_leaks": {},
           "hostile": {}}
    for s in "ABC":
        flt = {key: s}
        got = m.get_all(filters=flt)
        items = got.get("results", got) if isinstance(got, dict) else got
        texts = [it.get("memory", "") for it in items]
        res["get_all_leaks"][s] = sum(1 for t in texts if foreign_in(key, t, s))
        hits = 0
        for probe in facts[s][:3]:
            r = m.search(probe, filters=flt, top_k=5)
            rr = r.get("results", r) if isinstance(r, dict) else r
            hits += sum(1 for it in rr if foreign_in(key, it.get("memory", ""), s))
        res["search_leaks"][s] = hits
        rows = history_rows(hist)
        res["history_leaks"][s] = sum(
            1 for sc, _, c in rows
            if f"{key}={s}" in sc and foreign_in(key, c or "", s))
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
    return res


def run_mutation_control(mem_cls, stub_url, root, key, facts):
    """(b) drop the scope key from filter construction -> main MUST go red."""
    store = root / f"mut_{key}/store"
    hist = str(root / f"mut_{key}/history.db")
    m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
    for i in range(FACTS_PER):
        for s in "ABC":
            m.add([{"role": "user", "content": facts[s][i]}], infer=False, **{key: s})
    orig_search = type(m).search

    def mutated_search(self, query, filters=None, **kw):
        f = {k: v for k, v in (filters or {}).items() if k != key}
        return orig_search(self, query, filters=f, **kw)

    type(m).search = mutated_search
    try:
        leaks = 0
        for s in "ABC":
            r = m.search(facts[s][0], filters={key: s}, top_k=5)
            rr = r.get("results", r) if isinstance(r, dict) else r
            leaks += sum(1 for it in rr if foreign_in(key, it.get("memory", ""), s))
    finally:
        type(m).search = orig_search
    return {"leaks_detected": leaks, "fired": leaks > 0}


def run_shared_id_control(mem_cls, stub_url, root, key, facts):
    """(a) all subjects under ONE shared key value -> detector must fire."""
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
    return {"get_all_cross_items": leaks, "search_cross_items": sleaks,
            "fired": (leaks + sleaks) > 0}


def run_incident_demo(mem_cls, stub_url, root):
    """One user, SHARED history db -- the H5 channel; + run_id measurement."""
    out = {}
    # (i) same scope, two sessions
    store = root / "demo_same/store"
    hist = str(root / "demo_same/history.db")
    m = mem_cls.from_config(mem_cfg(stub_url, str(store), hist))
    sess1 = [{"role": "user", "content": f"demo s1 line {i} about kettles-{i}"} for i in range(8)]
    sess2 = [{"role": "user", "content": f"demo s2 line {i} about anchors-{i}"} for i in range(4)]
    m.add(sess1, user_id="u_demo", infer=False)
    m.add(sess2, user_id="u_demo", infer=False)
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
    m2.add(sess1, user_id="u_demo", run_id="q1", infer=False)
    m2.add(sess2, user_id="u_demo", run_id="q2", infer=False)
    rows2 = history_rows(hist2)
    q2_scope = [c for sc, _, c in rows2 if sc == "user_id=u_demo&run_id=q2"]
    q1_in_q2 = sum(1 for c in q2_scope if "kettles" in (c or ""))
    out["run_id"] = {"q2_scope_rows": len(q2_scope), "s1_rows_leaked_into_q2": q1_in_q2,
                     "run_id_isolates_tail": q1_in_q2 == 0}
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
    return out


def main():
    fp = announce({"runner": "evals/p4_mem0_isolation.py",
                   "llm": {"model": "stub-llm", "infer": "False (no generation)"},
                   "embedder": "stub (sha256-seeded 768-dim, deterministic)",
                   "vector_store": "qdrant local, temp dir",
                   "history_db": "temp per scenario (H5 lesson)",
                   "mem0_version": "v1.1", "scope_keys": list(KEYS),
                   "controls": ["shared-id", "mutational"],
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
    report["passed"] = bool(main_ok and controls_ok)
    import platform
    try:
        import subprocess
        pipmem = subprocess.run([sys.executable, "-m", "pip", "freeze"],
                                capture_output=True, text=True).stdout
        pipmem = "\n".join(l for l in pipmem.splitlines() if "mem0" in l.lower())
    except Exception:
        pipmem = "unavailable"
    report["environment"] = {"uname": os.uname().__dict__, "python": platform.python_version(),
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
