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

from mem0 import Memory

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
RESULTS = Path(__file__).resolve().parent / "results/pilot_evidence_n500.json"
KEY = open("/tmp/opencode/pilot8085.key").read().strip()
MODEL = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
EMB = "text-embedding-nomic-embed-text-v1.5"
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


def main():
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
                "openai_base_url": "http://127.0.0.1:8085/v1", "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": "http://127.0.0.1:1449/v1",
                "api_key": "local-smoke", "embedding_dims": 768}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"fix1_{qi_off}", "embedding_model_dims": 768,
                "path": f"{STORE}/q{qi_off}"}},
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