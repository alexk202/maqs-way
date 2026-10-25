#!/usr/bin/env python3
"""(b1) per council: single-session slice (156 q), OLD config (max_tokens 1200),
finish_reason counter ON — clean systemic truncation percent, unmasked.

Primary number: finish_reason=length share (systemic truncation, finally visible).
Secondary: evidence-R@5, empty-collection count (each empty = guaranteed miss).
Checkpoint per question. OLD config deliberately — fix run comes after.
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MEM0_TELEMETRY", "False")  # Oct-17 lesson: PostHog noise + ~/.mem0/migrations_qdrant lock
from isolation_guard import guarded, temp_history_db
from mem0 import Memory
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/mem0single156_{int(time.time())}"
N = 156  # 70 user + 56 assistant + 30 preference
finish_reasons = Counter()


def patch_llm_client(m):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        resp = orig(*a, **kw)
        try:
            finish_reasons[resp.choices[0].finish_reason] += 1
        except Exception:
            finish_reasons["unknown"] += 1
        return resp

    client.chat.completions.create = wrapped


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
                "model": MODEL, "temperature": 0, "max_tokens": 1200,  # OLD config deliberately
                "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": EMBED_BASE_URL,
                "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"s156_{qi}", "embedding_model_dims": EMBED_DIMS,
                "path": f"{STORE}/q{qi}"}},
            "history_db_path": temp_history_db(f"{STORE}/q{qi}"),
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        patch_llm_client(m)
        t0 = time.time()
        m.add(q["haystack_sessions"][0], user_id="u_pilot", infer=True)
        t_ing = time.time() - t0
        cnt = m.vector_store.client.count(f"s156_{qi}", exact=True).count
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
        results.append({
            "q_id": q["question_id"], "q_type": q["question_type"], "answer": q["answer"],
            "evidence_hit": ev_hit, "substr_hit": substr_hit,
            "memories": cnt, "ingest_s": round(t_ing, 1),
        })
        print(f"[{qi+1}/{N}] {q['question_type'][:24]:24s} ev_hit={ev_hit} mem={cnt} "
              f"ingest={t_ing:.0f}s")
        try:
            m.vector_store.client.close()
        except Exception:
            pass
        del m
        OUT.mkdir(exist_ok=True)
        (OUT / "single156_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": N,
            "finish_reasons": dict(finish_reasons),
            "results": results,
        }, indent=2, ensure_ascii=False))

    r5 = sum(1 for r in results if r["evidence_hit"]) / len(results)
    empties = sum(1 for r in results if r["memories"] == 0)
    total_calls = sum(finish_reasons.values())
    length_stops = finish_reasons.get("length", 0)
    print(f"\nevidence-R@5 = {r5:.3f} ({sum(1 for r in results if r['evidence_hit'])}/{len(results)})")
    print(f"empty collections: {empties}/{len(results)}")
    print(f"finish_reason: {dict(finish_reasons)} | length share: "
          f"{length_stops}/{total_calls} = {length_stops/max(1,total_calls)*100:.1f}%")
    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768,
            "embedder": EMB, "mem0": "0724291b",
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "metric": "1a evidence-session R@5 + finish_reason instrumentation",
            "selection": "single-session-156 (70 user + 56 assistant + 30 preference), committed order",
            "config": "OLD: max_tokens=1200 (deliberate, pre-fix baseline per council order)",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": len(results), "label": "unmasked systemic measure, pre-fix",
        },
        "R_at_5_evidence": r5,
        "empty_collections": empties,
        "finish_reasons": dict(finish_reasons),
        "results": results,
    }
    (OUT / "pilot_evidence_single156_oldcfg.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())