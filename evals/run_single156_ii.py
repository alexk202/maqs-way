#!/usr/bin/env python3
"""(ii) B6-over-grammar: single-156, config = (g1) EXACT + prompt=B6_VERBATIM (THE delta).

Answers the branch's target question with the first metric that sees it: R@5 is
saturated (g1 1.000) and blind to the B6 class; verbatim-recall v1.2 (council-classified
N1-N8, clean base 0.177 global / 0.162 panel) is the primary guard.
Prereg: evals/prereg-ii.md (review -> sanction -> commit -> run; NOT run before review).
Instrumentation: g1 frames + verbatim per-question (full-facts vs all-facts split,
per council), frozen pair panel (12 full ids from verbatim_g1_v12.json), unpredicted
register (owner protocol, first live use).
"""
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MEM0_TELEMETRY", "False")

from isolation_guard import guarded, temp_history_db
from mem0 import Memory
from qdrant_client import QdrantClient

from b6_prompt import B6_VERBATIM
from verbatim_v12 import classify_noise, norm, source_items
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
G1_RES = OUT / "pilot_evidence_single156_g1.json"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/mem0single156ii_{int(time.time())}"
N = 156
MAX_TOKENS = 2000  # g1/b2 exact

B6_SHA = hashlib.sha256(Path("evals/b6_prompt.py").read_bytes()).hexdigest()
G1_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "memory": {
            "type": "array", "maxItems": 31,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string", "maxLength": 900},
                    "linked_memory_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
                },
                "required": ["id", "text"],
            },
        },
    },
    "required": ["memory"],
}
G1_RF = {"type": "json_schema", "json_schema": {"name": "mem0_extraction_g1", "strict": True, "schema": G1_SCHEMA}}
SCHEMA_SHA = hashlib.sha256(json.dumps(G1_SCHEMA, sort_keys=True).encode()).hexdigest()
MAX_ITEMS = 31

PANEL = {  # frozen full ids, base recall_clean from verbatim_g1_v12.json
    "75832dbd": 0.070, "0a34ad58": 0.055, "1faac195": 0.138, "b0479f84": 0.093,
    "fca70973": 0.241, "311778f1": 0.205, "afdc33df": 0.027, "19b5f2b3": 0.162,
    "e47becba": 0.053, "58bf7951": 0.105, "3b6f954b": 0.526, "faba32e5": 0.263,
}
ALL_CALLS = []


def patch_llm_client(m, qi):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        kw["response_format"] = G1_RF
        try:
            resp = orig(*a, **kw)
        except Exception:
            ALL_CALLS.append({"q": qi, "fr": "exception", "parse": "n/a", "chars": 0,
                              "facts": None, "capped": None, "links_used": None,
                              "unique_texts": None, "facts_at_maxlen": None,
                              "max_fact_chars": None})
            raise
        fr = "unknown"
        content = ""
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            ALL_CALLS.append({"q": qi, "fr": fr, "parse": "n/a", "chars": 0,
                              "facts": None, "capped": None, "links_used": None,
                              "unique_texts": None, "facts_at_maxlen": None,
                              "max_fact_chars": None})
            return resp
        facts = capped = links_used = unique_texts = facts_at_maxlen = max_fact_chars = None
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory") if isinstance(d, dict) else None
            if isinstance(mem, list):
                texts = [it.get("text", "") for it in mem if isinstance(it, dict)]
                facts = len(mem)
                capped = (facts == MAX_ITEMS)
                links_used = sum(1 for it in mem
                                 if isinstance(it, dict) and it.get("linked_memory_ids"))
                unique_texts = len(set(texts))
                facts_at_maxlen = sum(1 for s in texts if len(s) == 900)
                max_fact_chars = max((len(s) for s in texts), default=0)
        except Exception:
            parse = "fail"
        ALL_CALLS.append({"q": qi, "fr": fr, "parse": parse, "chars": len(content),
                          "facts": facts, "capped": capped, "links_used": links_used,
                          "unique_texts": unique_texts, "facts_at_maxlen": facts_at_maxlen,
                          "max_fact_chars": max_fact_chars})
        return resp

    client.chat.completions.create = wrapped


def verbatim_of(q, texts):
    sess_text = "\n".join(str(mm.get("content", "")) for mm in q["haystack_sessions"][0])
    items, nums = source_items(sess_text)
    signal = []
    noise_n = 0
    for it in items:
        if classify_noise(it) is None:
            signal.append(it)
        else:
            noise_n += 1
    blob_all = norm(" ".join(texts))
    blob_full = norm(" ".join(t for t in texts if len(t) < 900))
    kept_full = sum(1 for it in signal if norm(it) in blob_full)
    kept_all = sum(1 for it in signal if norm(it) in blob_all)
    n_sig = len(signal)
    return {
        "n_signal": n_sig, "noise_filtered": noise_n,
        "recall_full": round(kept_full / n_sig, 3) if n_sig else None,
        "recall_all": round(kept_all / n_sig, 3) if n_sig else None,
        "n_nums": len(nums),
    }


@guarded()
def main():
    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant", "single-session-preference")]
    assert len(singles) == N, f"expected {N}, got {len(singles)}"

    results = []
    for qi, q in enumerate(singles):
        cfg = {
            "llm": {"provider": "openai", "config": {
                "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
                "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": EMBED_BASE_URL,
                "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"s156ii_{qi}", "embedding_model_dims": EMBED_DIMS,
                "path": f"{STORE}/q{qi}"}},
            "history_db_path": temp_history_db(f"{STORE}/q{qi}"),
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        q_calls_start = len(ALL_CALLS)
        patch_llm_client(m, qi)
        t0 = time.time()
        m.add(q["haystack_sessions"][0], user_id="u_pilot", infer=True, prompt=B6_VERBATIM)
        t_ing = time.time() - t0
        cnt = m.vector_store.client.count(f"s156ii_{qi}", exact=True).count
        t1 = time.time()
        res = m.search(q["question"], filters={"user_id": "u_pilot"}, top_k=5)
        items = res.get("results", res) if isinstance(res, dict) else res
        t_ret = time.time() - t1
        top5 = [(it.get("id"), it.get("memory", "")) for it in items]
        ans_sess = set(q["answer_session_ids"])
        sess_of_add = q["haystack_session_ids"][0]
        ev_hit = any(sess_of_add in ans_sess for _, _ in top5)
        q_calls = ALL_CALLS[q_calls_start:]
        client = m.vector_store.client
        pts, _ = client.scroll(collection_name=f"s156ii_{qi}", limit=200,
                              with_payload=True, with_vectors=False)
        texts = [r.payload.get("data", "") for r in pts]
        vb = verbatim_of(q, texts)
        try:
            client.close()
        except Exception:
            pass
        del m
        results.append({
            "q_id": q["question_id"], "q_type": q["question_type"], "answer": q["answer"],
            "evidence_hit": ev_hit, "memories": cnt, "ingest_s": round(t_ing, 1),
            "calls": len(q_calls),
            "call_frames": [
                {"fr": c["fr"], "parse": c["parse"], "chars": c["chars"],
                 "facts": c["facts"], "capped": c["capped"], "links_used": c["links_used"],
                 "unique_texts": c["unique_texts"], "facts_at_maxlen": c["facts_at_maxlen"],
                 "max_fact_chars": c["max_fact_chars"]}
                for c in q_calls
            ],
            "verbatim": vb,
        })
        print(f"[{qi+1}/{N}] {q['question_type'][:24]:24s} ev_hit={ev_hit} mem={cnt} "
              f"vb_full={vb['recall_full']} ingest={t_ing:.0f}s calls={len(q_calls)} "
              f"fr={dict(Counter(c['fr'] for c in q_calls))}")
        OUT.mkdir(exist_ok=True)
        (OUT / "single156_ii_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": N, "calls_total": len(ALL_CALLS),
            "results": results,
        }, indent=2, ensure_ascii=False))

    r5 = sum(1 for r in results if r["evidence_hit"]) / len(results)
    empties = sum(1 for r in results if r["memories"] == 0)
    total_calls = len(ALL_CALLS)
    fr_all = Counter(c["fr"] for c in ALL_CALLS)
    mal = sum(1 for c in ALL_CALLS if c["parse"] == "fail" and c["fr"] != "length")
    other_fail = sum(1 for c in ALL_CALLS if c["fr"] in ("exception", "unknown"))
    trunc = sum(1 for c in ALL_CALLS if c["fr"] == "length")
    capped_calls = sum(1 for c in ALL_CALLS if c["capped"])
    loop_calls = sum(1 for c in ALL_CALLS
                     if c["facts"] is not None and c["unique_texts"] is not None
                     and c["facts"] >= 2 * c["unique_texts"])
    facts_at_maxlen_total = sum(c["facts_at_maxlen"] or 0 for c in ALL_CALLS)

    sig = [(r["verbatim"]["n_signal"],
            r["verbatim"]["recall_full"] if r["verbatim"]["recall_full"] is not None else 0,
            r["q_id"]) for r in results if r["verbatim"]["n_signal"] > 0 and r["memories"] >= 5]
    tot_sig = sum(s[0] for s in sig)
    kept_sig = sum(round(s[0] * s[1]) for s in sig)
    global_clean_micro = round(kept_sig / max(1, tot_sig), 3)

    panel_rows = []
    for r in results:
        qid = r["q_id"]
        if qid in PANEL:
            panel_rows.append({"q_id": qid, "base": PANEL[qid],
                               "ii_recall": r["verbatim"]["recall_full"],
                               "ii_recall_all": r["verbatim"]["recall_all"],
                               "stored": r["memories"]})
    panel_vals = [p["ii_recall"] if p["ii_recall"] is not None else 0 for p in panel_rows]
    panel_mean = round(sum(panel_vals) / max(1, len(panel_vals)), 3)
    above_base = sum(1 for p in panel_rows
                     if (p["ii_recall"] or 0) > p["base"])
    panel_ok = len(panel_rows) == 12

    print(f"\nevidence-R@5 = {r5:.3f} ({sum(1 for r in results if r['evidence_hit'])}/{len(results)})")
    print(f"empty: {empties}/{len(results)} | mal {mal} | other_fail {other_fail} | trunc {trunc} "
          f"| capped {capped_calls} | loop {loop_calls} | at900 {facts_at_maxlen_total}")
    print(f"PRIMARY panel: mean_full={panel_mean} (>=0.32?) | above own base: {above_base}/12 "
          f"(>=8?) | panel complete: {panel_ok}")
    print(f"sanity global clean micro (full): {global_clean_micro} (>=0.35?)")
    nums_q = [r for r in results if r["verbatim"]["n_nums"] > 0]

    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768,
            "seed": 42, "repeat_penalty": "server default 1.0 (treatment deferred post-(ii))",
            "embedder": EMB, "mem0": "0724291b",
            "config": f"(ii): g1 EXACT + prompt=B6_VERBATIM (b6_prompt.py sha256 {B6_SHA[:16]}…); "
                      f"schema sha256 {SCHEMA_SHA[:16]}…; max_tokens={MAX_TOKENS}",
            "b6_prompt_sha256_file": B6_SHA,
            "schema_sha256": SCHEMA_SHA,
            "panel": "12 full ids frozen from verbatim_g1_v12.json (stratified 4/4/4)",
            "metric": "verbatim v1.2 (N1-N8 council classification), FULL-facts primary, "
                      "all-facts artifact line; R@5 non-regression",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": len(results), "label": "package-(ii) B6-over-grammar, prereg-ii",
        },
        "R_at_5_evidence": r5,
        "empty_collections": empties,
        "mal_calls": mal, "other_fail_calls": other_fail, "trunc_calls": trunc,
        "capped_calls": capped_calls, "loop_calls": loop_calls,
        "facts_at_maxlen_total": facts_at_maxlen_total,
        "primary_panel": {
            "mean_full": panel_mean, "threshold_P1": 0.32,
            "members_above_own_base": above_base, "threshold_P2": 8,
            "panel_complete": panel_ok, "rows": panel_rows,
        },
        "sanity_global_clean_micro_full": global_clean_micro,
        "sanity_threshold": 0.35,
        "global_clean_micro_all": None,
        "nums_questions": len(nums_q),
        "unpredicted": [],
        "results": results,
    }
    (OUT / "pilot_evidence_single156_ii.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print("artifact: evals/results/pilot_evidence_single156_ii.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
