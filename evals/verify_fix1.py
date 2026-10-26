#!/usr/bin/env python3
"""Verification of fix ① (max_tokens 2000) on the 4 failed questions, per council.

Instruments finish_reason == "length" with a permanent counter (monkeypatch on
the OpenAI client inside mem0) — truncation becomes a FACT, not an inference.
Re-ingests the 4 failed questions' sessions into FRESH collections; reports:
parse events (0 expected), finish_reason counts, memories produced.
"""
import json
import shutil
import time
from collections import Counter
from pathlib import Path

import os
os.environ.setdefault("MEM0_TELEMETRY", "False")  # Oct-17 lesson: PostHog noise + ~/.mem0/migrations_qdrant lock
from isolation_guard import guarded, temp_history_db
from config_fingerprint import announce
from mem0 import Memory
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
RESULTS = Path(__file__).resolve().parent / "results/pilot_evidence_n500.json"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/mem0verify_fix1_{int(time.time())}"  # fresh per run: stale lock class

finish_reasons = Counter()


def patch_llm_client(m):
    """Wrap chat.completions.create to count finish_reason — permanent, not one-shot."""
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
    fp = announce({"runner": "evals/verify_fix1.py", "max_tokens": 2000, "response_format": "mem0 default json_object (unenforced)", "add": "none", "selection": "b2 misses", "model": MODEL, "embedder": {"model": EMB, "dims": EMBED_DIMS}, "vector_store": "qdrant, fresh store per question", "history_db": "per-question temp (isolation)", "mem0_version": "v1.1"}, LLM_BASE_URL, label="evals/verify_fix1.py")
    d = json.loads(RESULTS.read_text())
    misses = [r for r in d["results"] if not r["evidence_hit"]]
    data = json.loads(DATA.read_text())
    by_qid = {q["question_id"]: q for q in data}

    shutil.rmtree(STORE, ignore_errors=True)
    total_mem = 0
    for qi_off, miss in enumerate(misses):
        q = by_qid[miss["q_id"]]
        cfg = {
            "llm": {"provider": "openai", "config": {
                "model": MODEL, "temperature": 0, "max_tokens": 2000,  # fix ①: 1200→2000
                "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": EMBED_BASE_URL,
                "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"fix1_{qi_off}", "embedding_model_dims": EMBED_DIMS,
                "path": f"{STORE}/q{qi_off}"}},
            "history_db_path": temp_history_db(f"{STORE}/q{qi_off}"),
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        patch_llm_client(m)
        for sess in q["haystack_sessions"]:
            m.add(sess, user_id="u_pilot", infer=True)
            time.sleep(1)
        # count memories via the SAME client the Memory holds (new client = lock clash)
        cnt = m.vector_store.client.count(f"fix1_{qi_off}", exact=True).count
        total_mem += cnt
        print(f"[{miss['q_id'][:8]}] {miss['q_type'][:24]:24s} answer={str(miss['answer'])[:28]!r:30s} "
              f"memories={cnt}")
        # close clients BEFORE reassigning m — migrations_qdrant lock class
        try:
            m.vector_store.client.close()
        except Exception:
            pass
        del m
    print(f"\nfinish_reason counter (permanent): {dict(finish_reasons)}")
    print(f"total memories produced across 4 previously-EMPTY collections: {total_mem}")
    return 0


if __name__ == "__main__":
    main()