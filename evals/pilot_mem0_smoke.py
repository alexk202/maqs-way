"""WP2 pilot SMOKE (synthetic, NOT a benchmark).

5 hand-written facts -> Mem0@0724291 (Chroma embedded, temp dir) with
Llama-3.1-8B (LLM_BASE_URL, temperature 0) + nomic-embed. Then 5 recall
probes. Any number below is connectivity smoke, NOT a calibration metric:
real R@5/temporal/abstention need vendored LongMemEval/LoCoMo (missing).

Exit 0 iff 5/5 recalled. Prints env provenance for the future real run.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)
from isolation_guard import guarded, temp_history_db

# Endpoints via eval_config (env-overridable; see evals/REPRODUCE.md).
LLM_BASE = LLM_BASE_URL
LLM_KEY = LLM_API_KEY
LLM = LLM_MODEL
EMB_BASE = EMBED_BASE_URL
EMB_KEY = EMBED_API_KEY
EMB = EMBED_MODEL

FACTS = [
    ("user_123", "My favourite programming language is Rust."),
    ("user_123", "I drink only green tea in the mornings."),
    ("user_123", "My dog is called Biscuit."),
    ("user_123", "I live in Yekaterinburg."),
    ("user_123", "My deadline for the report is 2026-11-01."),
]
PROBES = [
    ("user_123", "favourite programming language", "Rust"),
    ("user_123", "morning drink", "green tea"),
    ("user_123", "dog name", "Biscuit"),
    ("user_123", "where do I live", "Yekaterinburg"),
    ("user_123", "report deadline", "2026-11-01"),
]


@guarded()
def main() -> int:
    os.environ.setdefault("MEM0_TELEMETRY", "False")  # Oct-17 lesson: PostHog noise + migrations_qdrant lock
    from mem0 import Memory

    # infer mode via env: PILOT_INFER=1 -> full LLM extraction pipeline
    # (requires server ctx >= ~9k; our :8085 runs 16384). Default raw.
    infer = os.environ.get("PILOT_INFER") == "1"
    cfg = {
        "llm": {"provider": "openai", "config": {
            "model": LLM, "temperature": 0, "max_tokens": 200,
            "openai_base_url": LLM_BASE, "api_key": LLM_KEY}},
        "embedder": {"provider": "openai", "config": {
            "model": EMB, "openai_base_url": EMB_BASE, "api_key": EMB_KEY,
            "embedding_dims": EMBED_DIMS}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": "maqs_pilot_smoke",
            "embedding_model_dims": EMBED_DIMS,
            "path": "/tmp/opencode/mem0qdrant"}},
        "history_db_path": temp_history_db("/tmp/opencode/mem0qdrant_smoke"),
        "version": "v1.1",
    }
    print(json.dumps({"smoke": True, "benchmark": False,
                      "model": LLM, "embedder": EMB,
                      "mem0": "0724291b",
                      "ts": datetime.now(timezone.utc).isoformat(timespec="seconds")}))
    m = Memory.from_config(cfg)
    for uid, text in FACTS:
        t = time.time()
        m.add([{"role": "user", "content": text}], user_id=uid, infer=infer)
        print(f"stored in {time.time()-t:.1f}s: {text[:50]}")
        time.sleep(1)
    ok = 0
    for uid, q, want in PROBES:
        t = time.time()
        res = m.search(q, filters={"user_id": uid}, top_k=3)
        items = res.get("results", res) if isinstance(res, dict) else res
        texts = [it.get("memory", "") for it in items]
        hit = any(want.lower() in tx.lower() for tx in texts)
        ok += hit
        print(f"[{'HIT' if hit else 'MISS'}] {q!r} -> want {want!r} ({time.time()-t:.1f}s)")
        time.sleep(1)
    print(f"SCOPE: infer={'True (full LLM extraction)' if infer else 'False (raw storage+retrieval)'}")
    print(f"SMOKE {ok}/{len(PROBES)} recalled (synthetic, not benchmark)")
    return 0 if ok == len(PROBES) else 1


if __name__ == "__main__":
    sys.exit(main())
