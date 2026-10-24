#!/usr/bin/env python3
"""(b4) DIAGNOSTIC: single-session slice (156 q), config = (b3) + max_tokens 4000.

Purpose per prereg-b4.md: answer ONE question — is the b3 regression explained
by the max_tokens ceiling (delivery channel) or does a second prompt-side
effect exist? This is DIAGNOSIS, not a fix.

Deltas vs run_single156_b6.py (b3):
  1) max_tokens 2000 -> 4000 (fix-hypothesis ceiling; see Lock 2);
  2) per-call instrumentation (units closure, Lock 1): every wrapped LLM call
     logs (question index, finish_reason, parse outcome, response chars);
  3) bookkeeping (store prefix s156b4_, output filenames, provenance label).
Eval logic (data read, add, search, metrics) byte-identical otherwise;
prompt unchanged: B6_VERBATIM (fix ② under diagnosis, same wording).
Pre-registration: evals/prereg-b4.md (signed BEFORE run).
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MEM0_TELEMETRY", "False")

from mem0 import Memory

from b6_prompt import B6_VERBATIM
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/mem0single156b4_{int(time.time())}"
N = 156  # 70 user + 56 assistant + 30 preference
MAX_TOKENS = 4000  # Lock 2: 2x the observed b3 wall (2000, censored p99), see prereg

ALL_CALLS = []  # per-call records: {"q": qi-or-pre, "fr": finish_reason, "parse": ok|fail|n/a, "chars": int}


def patch_llm_client(m, qi):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        try:
            resp = orig(*a, **kw)
        except Exception as e:
            ALL_CALLS.append({"q": qi, "fr": "exception", "parse": "n/a", "chars": 0})
            raise
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            ALL_CALLS.append({"q": qi, "fr": "unknown", "parse": "n/a", "chars": 0})
            return resp
        try:
            json.loads(content)
            parse = "ok"
        except Exception:
            parse = "fail"
        ALL_CALLS.append({"q": qi, "fr": fr, "parse": parse, "chars": len(content)})
        return resp

    client.chat.completions.create = wrapped


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
                "collection_name": f"s156b4_{qi}", "embedding_model_dims": EMBED_DIMS,
                "path": f"{STORE}/q{qi}"}},
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        q_calls_start = len(ALL_CALLS)
        patch_llm_client(m, qi)
        t0 = time.time()
        m.add(q["haystack_sessions"][0], user_id="u_pilot", infer=True, prompt=B6_VERBATIM)
        t_ing = time.time() - t0
        cnt = m.vector_store.client.count(f"s156b4_{qi}", exact=True).count
        t1 = time.time()
        res = m.search(q["question"], filters={"user_id": "u_pilot"}, top_k=5)
        items = res.get("results", res) if isinstance(res, dict) else res
        t_ret = time.time() - t1
        top5 = [(it.get("id"), it.get("memory", "")) for it in items]
        ans_sess = set(q["answer_session_ids"])
        sess_of_add = q["haystack_session_ids"][0]
        ev_hit = any(sess_of_add in ans_sess for _, _ in top5)  # single session: any memory from it
        ans = str(q["answer"]).strip().lower()
        blob = " ".join(txt or "" for _, txt in top5).lower()
        substr_hit = bool(ans) and ans in blob
        q_calls = ALL_CALLS[q_calls_start:]
        results.append({
            "q_id": q["question_id"], "q_type": q["question_type"], "answer": q["answer"],
            "evidence_hit": ev_hit, "substr_hit": substr_hit,
            "memories": cnt, "ingest_s": round(t_ing, 1),
            "calls": len(q_calls),
            "call_frames": [
                {"fr": c["fr"], "parse": c["parse"], "chars": c["chars"]} for c in q_calls
            ],
        })
        print(f"[{qi+1}/{N}] {q['question_type'][:24]:24s} ev_hit={ev_hit} mem={cnt} "
              f"ingest={t_ing:.0f}s calls={len(q_calls)} "
              f"fr={dict(Counter(c['fr'] for c in q_calls))}")
        try:
            m.vector_store.client.close()
        except Exception:
            pass
        del m
        OUT.mkdir(exist_ok=True)
        (OUT / "single156_b4_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": N,
            "calls_total": len(ALL_CALLS),
            "results": results,
        }, indent=2, ensure_ascii=False))

    r5 = sum(1 for r in results if r["evidence_hit"]) / len(results)
    empties = sum(1 for r in results if r["memories"] == 0)
    total_calls = len(ALL_CALLS)
    fr_all = Counter(c["fr"] for c in ALL_CALLS)
    parse_fail_all = sum(1 for c in ALL_CALLS if c["parse"] == "fail")
    lens = sorted(c["chars"] for c in ALL_CALLS)
    print(f"\nevidence-R@5 = {r5:.3f} ({sum(1 for r in results if r['evidence_hit'])}/{len(results)})")
    print(f"empty collections: {empties}/{len(results)}")
    print(f"calls (wrapped): {total_calls} | finish_reason: {dict(fr_all)} | "
          f"length share: {fr_all.get('length', 0)}/{total_calls} = "
          f"{fr_all.get('length', 0)/max(1,total_calls)*100:.1f}%")
    print(f"parse fails (per-call): {parse_fail_all} | response chars p50/p99: "
          f"{lens[len(lens)//2]}/{lens[int(len(lens)*0.99)] if len(lens)>1 else '-'}")
    # empties attribution: questions with zero memories but zero parse fails
    empty_no_fail = sum(1 for r in results if r["memories"] == 0
                        and all(c["parse"] != "fail" for c in r["call_frames"]))
    print(f"empty questions with ZERO parse-fail calls: {empty_no_fail}")
    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768,
            "embedder": EMB, "mem0": "0724291b",
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "metric": "1a evidence-session R@5 + per-call instrumentation",
            "selection": "single-session-156 (70 user + 56 assistant + 30 preference), committed order",
            "config": f"DIAGNOSTIC: max_tokens={MAX_TOKENS}, B6_VERBATIM unchanged",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": len(results), "label": "diagnosis-not-fix, prereg-b4",
        },
        "R_at_5_evidence": r5,
        "empty_collections": empties,
        "empty_no_parse_fail": empty_no_fail,
        "calls_total": total_calls,
        "finish_reasons": dict(fr_all),
        "parse_fails_total": parse_fail_all,
        "response_chars_p99": lens[int(len(lens)*0.99)] if len(lens) > 1 else None,
        "results": results,
    }
    (OUT / "pilot_evidence_single156_b4.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
