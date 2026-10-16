"""WP2 pilot: LongMemEval-oracle R@5 on n=5 questions (NOT normative).

Stratified n=5 (one per q_type). Fresh Qdrant per question (no cross-bleed).
Ingest = evidence sessions only (oracle), infer=True (Llama-3.1-8B Q4 ctx
32768 on :8085), chunk sessions that would overflow the extraction prompt.
Metric: R@5 = answer substring present in top-5 extracted memories
(retrieval-side; abstention/generation metrics are a separate stage).

Every number carries provenance. n=5 pilot -> sizing table, nothing more.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

BASE = "http://127.0.0.1:8085/v1"
KEY = os.environ["PILOT_LLM_KEY"]
MODEL = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
EMB = "text-embedding-nomic-embed-text-v1.5"
EMB_BASE = os.environ.get("PILOT_EMB_BASE", "http://127.0.0.1:1449/v1")
EMB_KEY = os.environ.get("PILOT_EMB_KEY", "local-smoke")
DATA = Path(__file__).resolve().parent / "datasets" / "longmemeval" / "longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
N = 5
CTX_LIMIT = 24000  # prompt budget under 32768 ctx (headroom for response)
CHARS_PER_TOK = 4.0
# Fresh store dir per run: killed/interrupted runs can never poison the next
# one via a stale Qdrant local lock (class fix, not retry).
STORE = Path("/tmp/opencode") / f"mem0lme_{int(time.time())}"

PICK = ["temporal-reasoning", "multi-session", "knowledge-update",
        "single-session-user", "single-session-assistant"]


def main() -> int:
    from mem0 import Memory

    data = json.loads(DATA.read_text())
    questions = []
    for want in PICK:
        q = next(x for x in data if x["question_type"] == want)
        questions.append(q)

    results = []
    for qi, q in enumerate(questions):
        coll = f"lme_n5_{qi}"
        cfg = {
            "llm": {"provider": "openai", "config": {
                "model": MODEL, "temperature": 0, "max_tokens": 1200,
                "openai_base_url": BASE, "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": EMB_BASE, "api_key": EMB_KEY,
                "embedding_dims": 768}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": coll, "embedding_model_dims": 768,
                "path": str(STORE / f"q{qi}")}},
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        t0 = time.time()
        adds = 0
        for si, sess in enumerate(q["haystack_sessions"]):
            chars = sum(len(str(msg.get("content", ""))) for msg in sess)
            chunks = max(1, int(chars / (CTX_LIMIT * CHARS_PER_TOK)) + 1)
            size = max(1, len(sess) // chunks)
            for ci in range(chunks):
                part = sess[ci * size:(ci + 1) * size] if chunks > 1 else sess
                if not part:
                    continue
                m.add(part, user_id="u_pilot", infer=True)
                adds += 1
                time.sleep(1)
        t_ing = time.time() - t0
        t1 = time.time()
        res = m.search(q["question"], filters={"user_id": "u_pilot"}, top_k=5)
        items = res.get("results", res) if isinstance(res, dict) else res
        texts = [it.get("memory", "") for it in items]
        ans = str(q["answer"]).strip().lower()
        stop = {"the", "a", "an", "my", "i", "was", "is", "of", "to", "and", "in", "on", "for", "with", "had", "have", "it", "that"}
        atoks = [w for w in ans.split() if w not in stop and len(w) > 2]
        def _hit(texts):
            blob = " ".join(texts).lower()
            if ans and ans in blob:
                return True
            if not atoks:
                return False
            covered = sum(1 for w in atoks if w in blob)
            return covered / len(atoks) >= 0.6  # extraction paraphrases; majority-token proxy
        hit = _hit(texts)
        t_ret = time.time() - t1
        results.append({
            "q_id": q["question_id"], "q_type": q["question_type"],
            "answer": q["answer"], "hit": bool(hit),
            "sessions": len(q["haystack_sessions"]), "add_calls": adds,
            "ingest_s": round(t_ing, 1), "retrieve_s": round(t_ret, 1),
            "top5_preview": texts[:5],
        })
        print(f"[{qi+1}/{N}] {q['question_type']} hit={hit} "
              f"sessions={len(q['haystack_sessions'])} adds={adds} "
              f"ingest={t_ing:.0f}s retrieve={t_ret:.1f}s")
    r5 = sum(1 for r in results if r["hit"]) / len(results)
    total_ing = sum(r["ingest_s"] for r in results)
    OUT.mkdir(exist_ok=True)
    out = {
        "provenance": {
            "model": MODEL, "server": BASE, "ctx": 32768,
            "embedder": EMB, "mem0": "0724291b",
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": N, "label": "n=5 pilot, NOT normative, single-point",
        },
        "R_at_5": r5, "ingest_total_s": round(total_ing, 1),
        "extrapolation_50q_min": round(total_ing / N * 50 / 60, 1),
        "extrapolation_500q_h": round(total_ing / N * 500 / 3600, 1),
        "results": results,
    }
    (OUT / "pilot_n5.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"R@5 (n={N}) = {r5:.2f} | ingest total {total_ing:.0f}s "
          f"| 50q ~{out['extrapolation_50q_min']}min | 500q ~{out['extrapolation_500q_h']}h")
    return 0


if __name__ == "__main__":
    sys.exit(main())
