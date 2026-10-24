"""WP2 protocol metric 1a: evidence-session retrieval R@5 (LongMemEval-oracle).

Per question: ingest evidence sessions, TAG every produced/updated memory id
with the session that produced it (add() events), then search top-5 and hit
iff a retrieved memory's session tag intersects answer_session_ids.
This is the retrieval-side LongMemEval protocol (no generation, no judge).
Answer-substring rate is reported alongside for transparency only.

n=5 pilot, NOT normative. Fresh store per question. Provenance in output.
"""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

BASE = LLM_BASE_URL
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
EMB_BASE = EMBED_BASE_URL
EMB_KEY = EMBED_API_KEY
DATA = Path(__file__).resolve().parent / "datasets" / "longmemeval" / "longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
N = int(os.environ.get("PILOT_N", "50"))
MODE = os.environ.get("PILOT_MODE", "first50")  # first50 | stratified
# stratified: largest-remainder allocation of N over dataset q_type
# distribution, first-k-per-type in committed order (deterministic, pre-registered)


def select_questions(data, n, mode):
    if mode == "first50":
        return data[:n]
    from collections import Counter
    dist = Counter(x["question_type"] for x in data)
    alloc = {t: int(n * c / len(data)) for t, c in dist.items()}
    rem = n - sum(alloc.values())
    for t in sorted(dist, key=lambda t: (n * dist[t] / len(data)) % 1, reverse=True)[:rem]:
        alloc[t] += 1
    out, seen = [], Counter()
    for x in data:
        t = x["question_type"]
        if seen[t] < alloc.get(t, 0):
            out.append(x)
            seen[t] += 1
    return out
CTX_LIMIT = 24000
CHARS_PER_TOK = 4.0
STORE = Path("/tmp/opencode") / f"mem0ev_{int(time.time())}"

PICK = ["temporal-reasoning", "multi-session", "knowledge-update",
        "single-session-user", "single-session-assistant"]


def main() -> int:
    os.environ.setdefault("MEM0_TELEMETRY", "False")  # Oct-17 lesson: PostHog noise + migrations_qdrant lock
    from mem0 import Memory

    data = json.loads(DATA.read_text())
    questions = select_questions(data, N, MODE)

    results = []
    for qi, q in enumerate(questions):
        cfg = {
            "llm": {"provider": "openai", "config": {
                "model": MODEL, "temperature": 0, "max_tokens": 1200,
                "openai_base_url": BASE, "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": EMB_BASE, "api_key": EMB_KEY,
                "embedding_dims": EMBED_DIMS}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"ev_{qi}", "embedding_model_dims": EMBED_DIMS,
                "path": str(STORE / f"q{qi}")}},
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
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
        results.append({
            "q_id": q["question_id"], "q_type": q["question_type"],
            "answer": q["answer"],
            "evidence_hit": ev_hit, "substr_hit": substr_hit,
            "sessions": len(q["haystack_sessions"]), "add_calls": adds,
            "ingest_s": round(t_ing, 1), "retrieve_s": round(t_ret, 1),
            "tagged": len(tags),
            "top5": [{"id": mid, "sessions": sorted(tags.get(mid, set())), "text": (txt or "")[:80]}
                     for mid, txt in top5],
        })
        print(f"[{qi+1}/{N}] {q['question_type']} evidence_hit={ev_hit} "
              f"substr={substr_hit} ingest={t_ing:.0f}s")
        # Incremental checkpoint: a 9h run must not die with zero evidence.
        OUT.mkdir(exist_ok=True)
        (OUT / "pilot_evidence_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": N,
            "evidence_hits": sum(1 for r in results if r["evidence_hit"]),
            "results": results,
        }, indent=2, ensure_ascii=False))
    r5 = sum(1 for r in results if r["evidence_hit"]) / len(results)
    rs = sum(1 for r in results if r["substr_hit"]) / len(results)
    total_ing = sum(r["ingest_s"] for r in results)
    OUT.mkdir(exist_ok=True)
    outname = f"pilot_evidence_n{len(results)}{'_stratified' if MODE == 'stratified' else ''}.json"
    out = {
        "provenance": {
            "model": MODEL, "server": BASE, "ctx": 32768, "embedder": EMB,
            "mem0": "0724291b",
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "metric": "1a evidence-session retrieval R@5 (no generation)",
            "selection": MODE,
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": N, "label": "n=5 pilot, NOT normative, single-point",
        },
        "R_at_5_evidence": r5, "substr_rate": rs,
        "ingest_total_s": round(total_ing, 1),
        "extrapolation_50q_min": round(total_ing / N * 50 / 60, 1),
        "extrapolation_500q_h": round(total_ing / N * 500 / 3600, 1),
        "results": results,
    }
    (OUT / outname).write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"R@5 evidence (n={N}) = {r5:.2f} | substr = {rs:.2f} "
          f"| ingest {total_ing:.0f}s | 50q ~{out['extrapolation_50q_min']}min "
          f"| 500q ~{out['extrapolation_500q_h']}h")
    return 0


if __name__ == "__main__":
    sys.exit(main())