#!/usr/bin/env python3
"""(b3) B6 fix run: single-session slice (156 q), config = (b2) FIX + B6 verbatim
prompt. ONLY deltas vs run_single156_fixcfg.py: (1) prompt=B6_VERBATIM on add,
(2) bookkeeping (store prefix s156b6_, output filenames, provenance label,
MEM0_TELEMETRY env hygiene). Eval logic byte-identical otherwise.

Primary number: B6-class misses (title lost in paraphrase) — target 0.
Secondary: evidence-R@5 (guard vs b2 0.987), empty collections,
finish_reason length share + dual parse-failure counter (must not regress).
Checkpoint per question. Pre-registration: evals/prereg-b6.md (signed before run).
"""
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MEM0_TELEMETRY", "False")

from isolation_guard import guarded, temp_history_db
from config_fingerprint import announce
from mem0 import Memory

from b6_prompt import B6_VERBATIM
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/mem0single156b6_{int(time.time())}"
N = 156  # 70 user + 56 assistant + 30 preference
finish_reasons = Counter()
parse_failures = Counter()  # dual counter per council: truncation-class vs malformed-class


def patch_llm_client(m):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        resp = orig(*a, **kw)
        try:
            fr = resp.choices[0].finish_reason
            finish_reasons[fr] += 1
            content = resp.choices[0].message.content or ""
            try:
                json.loads(content)
            except Exception:
                # parse will fail downstream too — classify NOW by finish_reason
                if fr == "length":
                    parse_failures["truncation_class"] += 1
                else:
                    parse_failures["malformed_class"] += 1
        except Exception:
            finish_reasons["unknown"] += 1
        return resp

    client.chat.completions.create = wrapped


@guarded()
def main():
    fp = announce({"runner": "evals/run_single156_b6.py", "max_tokens": 2000, "response_format": "mem0 default json_object (unenforced)", "add": "B6_VERBATIM (prereg sha 73c485c1)", "selection": "single-156 committed order", "model": MODEL, "embedder": {"model": EMB, "dims": EMBED_DIMS}, "vector_store": "qdrant, fresh store per question", "history_db": "per-question temp (isolation)", "mem0_version": "v1.1"}, LLM_BASE_URL, label="evals/run_single156_b6.py")
    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant", "single-session-preference")]
    assert len(singles) == N, f"expected {N}, got {len(singles)}"

    results = []
    for qi, q in enumerate(singles):
        cfg = {
            "llm": {"provider": "openai", "config": {
                "model": MODEL, "temperature": 0, "max_tokens": 2000,  # fix ① carried from (b2)
                "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": EMBED_BASE_URL,
                "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"s156b6_{qi}", "embedding_model_dims": EMBED_DIMS,
                "path": f"{STORE}/q{qi}"}},
            "history_db_path": temp_history_db(f"{STORE}/q{qi}"),
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        patch_llm_client(m)
        t0 = time.time()
        m.add(q["haystack_sessions"][0], user_id="u_pilot", infer=True, prompt=B6_VERBATIM)  # fix ② — the ONLY eval delta vs (b2)
        t_ing = time.time() - t0
        cnt = m.vector_store.client.count(f"s156b6_{qi}", exact=True).count
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
        (OUT / "single156_b6_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": N,
            "finish_reasons": dict(finish_reasons),
            "parse_failures": dict(parse_failures),
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
    print(f"parse failures (dual counter): {dict(parse_failures)}")
    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768,
            "embedder": EMB, "mem0": "0724291b",
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "metric": "1a evidence-session R@5 + finish_reason instrumentation",
            "selection": "single-session-156 (70 user + 56 assistant + 30 preference), committed order",
            "config": "FIX2: max_tokens=2000 + B6 verbatim prompt (only eval delta vs b2)",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": len(results), "label": "unmasked systemic measure, B6 fix",
        },
        "R_at_5_evidence": r5,
        "empty_collections": empties,
        "finish_reasons": dict(finish_reasons),
        "parse_failures": dict(parse_failures),
        "results": results,
    }
    out["provenance"].update(fp)
    (OUT / "pilot_evidence_single156_b6.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
