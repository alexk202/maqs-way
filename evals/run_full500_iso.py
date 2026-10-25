#!/usr/bin/env python3
"""full-500-iso: ISOLATED re-measurement of the frozen full-500 (prereg-full500-iso).

Config = frozen full-500 of 2026-10-17 (restored from commits 6f44afc +
bd2ca0d): first 500 dataset questions, max_tokens 1200, temperature 0,
chunking CTX_LIMIT 24000 x CHARS_PER_TOK 4.0, fresh store per question,
nomic embedder, ctx 32768 server. The ONLY intentional delta: per-question
history isolation (history_db_path -> per-question temp store; already in the
runner family since 9d61d10).

Non-config deltas (disclosed in the prereg, observation-only):
  1. wrapped-client instrumentation (fr/parse/chars/facts + RAW extraction
     dumps per call) for the mal/trunc gates and byte-level evidence --
     no response_format injection, the request kwargs are untouched;
  2. renamed outputs -- the frozen pilot_evidence_n500.json is never
     overwritten (artifact: pilot_evidence_n500_iso.json, checkpoint:
     pilot_evidence_n500_iso_partial.json);
  3. H5 guard (observation), Wilson CI in the artifact.

NOT RUN before the owner signs prereg-full500-iso.md.
"""
import json
import math
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)
from isolation_guard import guarded, temp_history_db

BASE = LLM_BASE_URL
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
EMB_BASE = EMBED_BASE_URL
EMB_KEY = EMBED_API_KEY
DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
N = 500  # frozen full-500: data[:500] (MODE first50 with N=500)
CTX_LIMIT = 24000
CHARS_PER_TOK = 4.0
STORE = Path("/tmp/opencode") / f"full500iso_{int(time.time())}"

CALLS = []  # {"q", "fr", "parse", "chars", "facts", "raw"}


def patch_llm_client(m, qi):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        # observation-only: kw is NOT modified (no response_format injection;
        # the frozen config used mem0's default json_object)
        try:
            resp = orig(*a, **kw)
        except Exception:
            CALLS.append({"q": qi, "fr": "exception", "parse": "n/a",
                          "chars": 0, "facts": None, "raw": ""})
            raise
        fr, content = "unknown", ""
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            CALLS.append({"q": qi, "fr": fr, "parse": "n/a", "chars": 0,
                          "facts": None, "raw": ""})
            return resp
        facts = None
        parse = "n/a"
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory") if isinstance(d, dict) else None
            if isinstance(mem, list):
                facts = len(mem)
        except Exception:
            parse = "fail"
        CALLS.append({"q": qi, "fr": fr, "parse": parse, "chars": len(content),
                      "facts": facts, "raw": content})
        return resp

    client.chat.completions.create = wrapped


def wilson(p, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    den = 1 + z * z / n
    center = (p + z * z / (2 * n)) / den
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (round(max(0.0, center - half), 4), round(min(1.0, center + half), 4))


def make_cfg(coll_name, store_path, hist_path):
    """THE config of this run (full-500-iso); shared by the main run and the
    mini-control so the control provably runs THIS run's config."""
    return {
        "llm": {"provider": "openai", "config": {
            "model": MODEL, "temperature": 0, "max_tokens": 1200,
            "openai_base_url": BASE, "api_key": KEY}},
        "embedder": {"provider": "openai", "config": {
            "model": EMB, "openai_base_url": EMB_BASE, "api_key": EMB_KEY,
            "embedding_dims": EMBED_DIMS}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": coll_name, "embedding_model_dims": EMBED_DIMS,
            "path": store_path}},
        "history_db_path": hist_path,
        "version": "v1.1",
    }


MINI5 = ["75832dbd", "0a34ad58", "1faac195", "b0479f84", "fca70973"]


def run_mini_control() -> int:
    """Prereg sec 3 mini-control: 5 panel-12 questions in THIS run's config,
    two passes BEFORE the start, byte-identity of raw extraction outputs.
    Divergence -> recorded, the main run is NOT blocked (aggregate conclusions
    stand); per-question conclusions for full-500-iso become invalid."""
    from mem0 import Memory
    data = json.loads(DATA.read_text())
    by8 = {q["question_id"].split("_")[-1]: q for q in data}
    mini = [by8[h] for h in MINI5]

    passes = []
    for pi in range(2):
        results = []
        for qi, q in enumerate(mini):
            cfg = make_cfg(f"mini_{pi}_{qi}", str(STORE / f"mini/pass{pi}/q{qi}"),
                           temp_history_db(f"{STORE}/mini/pass{pi}/q{qi}"))
            m = Memory.from_config(cfg)
            calls_start = len(CALLS)
            patch_llm_client(m, qi)
            t0 = time.time()
            for sess in q["haystack_sessions"]:
                chars = sum(len(str(msg.get("content", ""))) for msg in sess)
                chunks = max(1, int(chars / (CTX_LIMIT * CHARS_PER_TOK)) + 1)
                size = max(1, len(sess) // chunks)
                for ci in range(chunks):
                    part = sess[ci * size:(ci + 1) * size] if chunks > 1 else sess
                    if not part:
                        continue
                    m.add(part, user_id="u_pilot", infer=True)
                    time.sleep(1)
            try:
                ga = m.get_all(filters={"user_id": "u_pilot"})
                stored = sorted(it.get("memory", "") for it in ga.get("results", ga))
            except Exception:
                stored = []
            qcalls = CALLS[calls_start:]
            results.append({
                "q_id": q["question_id"],
                "frames": [{"fr": c["fr"], "parse": c["parse"], "chars": c["chars"],
                            "facts": c["facts"]} for c in qcalls],
                "raw_outputs": [c["raw"] for c in qcalls],
                "stored_texts": stored,
                "ingest_s": round(time.time() - t0, 1),
            })
            print(f"[mini pass {pi + 1}/2][{qi + 1}/5] {q['question_id'][:12]} "
                  f"calls={len(qcalls)}", flush=True)
            try:
                m.vector_store.client.close()
            except Exception:
                pass
            del m
        passes.append(results)

    per_q, ident = [], 0
    for qi in range(len(mini)):
        a, b = passes[0][qi], passes[1][qi]
        ok = (a["raw_outputs"] == b["raw_outputs"] and
              a["stored_texts"] == b["stored_texts"] and a["frames"] == b["frames"])
        ident += ok
        per_q.append({"q_id": a["q_id"], "byte_identical": ok,
                      "raw_identical": a["raw_outputs"] == b["raw_outputs"],
                      "stored_identical": a["stored_texts"] == b["stored_texts"],
                      "frames_identical": a["frames"] == b["frames"]})
    out = {
        "provenance": {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": "full-500-iso mini-control (prereg sec 3): 5 panel-12 ids, "
                     "THIS run's config via make_cfg, 2 passes before the start",
            "question_ids": MINI5,
            "rule": "divergence recorded, main run NOT blocked; per-question "
                    "conclusions for full-500-iso invalid on divergence",
        },
        "identical": ident, "of": len(mini), "per_question": per_q,
        "passes": passes,
    }
    (OUT / "full500iso_minicontrol.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"MINI-CONTROL: {ident}/5 byte-identical "
          f"({'IDENTICAL' if ident == len(mini) else 'DIVERGENCE RECORDED (non-blocking)'})",
          flush=True)
    return 0 if ident == len(mini) else 1


def run_full500() -> int:
    os.environ.setdefault("MEM0_TELEMETRY", "False")  # Oct-17 lesson: PostHog noise + migrations_qdrant lock
    from mem0 import Memory

    data = json.loads(DATA.read_text())
    questions = data[:N]  # frozen selection: first 500, committed order
    assert len(questions) == N

    results = []
    for qi, q in enumerate(questions):
        cfg = make_cfg(f"ev_{qi}", str(STORE / f"q{qi}"),
                       temp_history_db(f"{STORE}/q{qi}"))
        m = Memory.from_config(cfg)
        calls_start = len(CALLS)
        patch_llm_client(m, qi)
        t0 = time.time()
        tags = {}  # mem_id -> set(session_ids that produced/updated it)
        adds = 0
        for si, sess in enumerate(q["haystack_sessions"]):
            sid = q["haystack_session_ids"][si]
            chars = sum(len(str(msg.get("content", ""))) for msg in sess)
            chunks = max(1, int(chars / (CTX_LIMIT * CHARS_PER_TOK)) + 1)
            size = max(1, len(sess) // chunks)
            for ci in range(chunks):
                part = sess[ci * size:(ci + 1) * size] if chunks > 1 else sess
                if not part:
                    continue
                out = m.add(part, user_id="u_pilot", infer=True)
                for ev in out.get("results", []):
                    if ev.get("id"):
                        tags.setdefault(ev["id"], set()).add(sid)
                adds += 1
                time.sleep(1)
        t_ing = time.time() - t0
        t1 = time.time()
        res = m.search(q["question"], filters={"user_id": "u_pilot"}, top_k=5)
        items = res.get("results", res) if isinstance(res, dict) else res
        t_ret = time.time() - t1
        top5 = [(it.get("id"), it.get("memory", "")) for it in items]
        ans_sessions = set(q["answer_session_ids"])
        ev_hit = any(any(s in ans_sessions for s in tags.get(mid, set()))
                     for mid, _ in top5)
        ans = str(q["answer"]).strip().lower()
        blob = " ".join(txt or "" for _, txt in top5).lower()
        substr_hit = bool(ans) and ans in blob
        qcalls = CALLS[calls_start:]
        results.append({
            "q_id": q["question_id"], "q_type": q["question_type"],
            "answer": q["answer"],
            "evidence_hit": ev_hit, "substr_hit": substr_hit,
            "sessions": len(q["haystack_sessions"]), "add_calls": adds,
            "ingest_s": round(t_ing, 1), "retrieve_s": round(t_ret, 1),
            "tagged": len(tags),
            "call_frames": [{"fr": c["fr"], "parse": c["parse"],
                             "chars": c["chars"], "facts": c["facts"]}
                            for c in qcalls],
            "raw_outputs": [c["raw"] for c in qcalls],
            "top5": [{"id": mid, "sessions": sorted(tags.get(mid, set())), "text": (txt or "")[:80]}
                     for mid, txt in top5],
        })
        print(f"[{qi+1}/{N}] {q['question_type']} evidence_hit={ev_hit} "
              f"substr={substr_hit} ingest={t_ing:.0f}s calls={len(qcalls)} "
              f"fr={dict(Counter(c['fr'] for c in qcalls))}", flush=True)
        # Incremental checkpoint: a long run must not die with zero evidence.
        OUT.mkdir(exist_ok=True)
        (OUT / "pilot_evidence_n500_iso_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": N,
            "evidence_hits": sum(1 for r in results if r["evidence_hit"]),
            "results": results,
        }, indent=2, ensure_ascii=False))
        try:
            m.vector_store.client.close()
        except Exception:
            pass
        del m
    r5 = sum(1 for r in results if r["evidence_hit"]) / len(results)
    rs = sum(1 for r in results if r["substr_hit"]) / len(results)
    total_ing = sum(r["ingest_s"] for r in results)
    empty = sum(1 for r in results if r["tagged"] == 0)
    total_mem = sum(r["tagged"] for r in results)
    mal = sum(1 for c in CALLS if c["parse"] == "fail" and c["fr"] != "length")
    other_fail = sum(1 for c in CALLS if c["fr"] in ("exception", "unknown"))
    trunc = sum(1 for c in CALLS if c["fr"] == "length")
    OUT.mkdir(exist_ok=True)
    out = {
        "provenance": {
            "model": MODEL, "server": BASE, "ctx": 32768, "embedder": EMB,
            "mem0": "0724291b", "seed": 42,
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "metric": "1a evidence-session retrieval R@5 (no generation)",
            "selection": "first 500, committed order (frozen full-500 selection)",
            "delta_vs_frozen": "per-question history isolation ONLY (prereg-full500-iso)",
            "stand_deltas": "see prereg-full500-iso.md (seed pinned 42, build 9177, telemetry off)",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": N, "label": "first isolated full-500 (prereg-full500-iso)",
        },
        "R_at_5_evidence": r5,
        "R_at_5_wilson_ci": wilson(r5, N),
        "substr_rate": rs,
        "empty_questions": empty,
        "total_tagged_memories": total_mem,
        "mal_calls": mal, "other_fail_calls": other_fail, "trunc_calls": trunc,
        "calls_total": len(CALLS),
        "ingest_total_s": round(total_ing, 1),
        "results": results,
    }
    (OUT / "pilot_evidence_n500_iso.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"R@5 evidence (n={N}) = {r5:.4f} Wilson {out['R_at_5_wilson_ci']} | "
          f"substr = {rs:.3f} | empty = {empty} | total_tagged = {total_mem} | "
          f"mal = {mal} | ingest {total_ing:.0f}s", flush=True)
    return 0


@guarded()
def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "mini":
        return run_mini_control()
    return run_full500()


if __name__ == "__main__":
    sys.exit(main())
