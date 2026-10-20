#!/usr/bin/env python3
"""(probe) Lock 4: re-run ONLY the 11 questions that were empty in b3, with b3 config
(max_tokens 2000 + B6_VERBATIM unchanged) and per-call instrumentation.

Purpose: answer Лумин's Lock 4 BEFORE b4 — were the 11 empty questions limited by the
2000-token wall (length / near-wall chars), or did extraction validly return empty?
Diagnosis only; no fix claims. Pre-registration: evals/prereg-b3-empty-probe.md.
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

DATA = Path("/home/aleksandr/Projects/MAQS_Way/evals/datasets/longmemeval/longmemeval_oracle.json")
OUT = Path("/home/aleksandr/Projects/MAQS_Way/evals/results")
KEY = open("/tmp/opencode/pilot8085.key").read().strip()
MODEL = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
EMB = "text-embedding-nomic-embed-text-v1.5"
STORE = f"/tmp/opencode/mem0probe11_{int(time.time())}"
MAX_TOKENS = 2000  # b3 config, unchanged (diagnosis of b3)
EMPTY_QIDS = [
    "001be529", "06878be2", "118b2229", "352ab8bd", "4baee567",
    "75f70248", "7a8d0b71", "8752c811", "8cf51dda", "af8d2e46", "b759caee",
]
ALL_CALLS = []


def patch_llm_client(m, qi):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        try:
            resp = orig(*a, **kw)
        except Exception:
            ALL_CALLS.append({"q": qi, "fr": "exception", "parse": "n/a", "chars": 0})
            raise
        fr = "unknown"
        content = ""
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            ALL_CALLS.append({"q": qi, "fr": fr, "parse": "n/a", "chars": 0})
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
    by_id = {q["question_id"][:8]: q for q in data}
    missing = [x for x in EMPTY_QIDS if x not in by_id]
    assert not missing, f"qids not found: {missing}"
    targets = [by_id[x] for x in EMPTY_QIDS]

    results = []
    for qi, q in enumerate(targets):
        cfg = {
            "llm": {"provider": "openai", "config": {
                "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
                "openai_base_url": "http://127.0.0.1:8085/v1", "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": "http://127.0.0.1:1449/v1",
                "api_key": "local-smoke", "embedding_dims": 768}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"probe11_{qi}", "embedding_model_dims": 768,
                "path": f"{STORE}/q{qi}"}},
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        start = len(ALL_CALLS)
        patch_llm_client(m, qi)
        t0 = time.time()
        m.add(q["haystack_sessions"][0], user_id="u_pilot", infer=True, prompt=B6_VERBATIM)
        t_ing = time.time() - t0
        cnt = m.vector_store.client.count(f"probe11_{qi}", exact=True).count
        frames = ALL_CALLS[start:]
        results.append({
            "q_id": q["question_id"][:8], "memories": cnt, "ingest_s": round(t_ing, 1),
            "calls": len(frames),
            "call_frames": [{"fr": c["fr"], "parse": c["parse"], "chars": c["chars"]}
                            for c in frames],
        })
        print(f"[{qi+1}/{len(targets)}] {q['question_id'][:8]} mem={cnt} calls={len(frames)} "
              f"fr={[c['fr'] for c in frames]} chars={[c['chars'] for c in frames]}")
        try:
            m.vector_store.client.close()
        except Exception:
            pass
        del m
        OUT.mkdir(exist_ok=True)
        (OUT / "probe11_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": len(targets), "results": results,
        }, indent=2, ensure_ascii=False))

    fr_all = Counter(c["fr"] for c in ALL_CALLS)
    walls = sum(1 for c in ALL_CALLS if c["fr"] == "length")
    near = sum(1 for c in ALL_CALLS if c["chars"] >= 7000)
    out = {
        "provenance": {
            "model": MODEL, "server": "http://127.0.0.1:8085/v1", "ctx": 32768,
            "embedder": EMB, "mem0": "0724291b",
            "dataset": "longmemeval_oracle.json (same slice), 11 b3-empty q_ids",
            "config": f"b3 config: max_tokens={MAX_TOKENS} + B6_VERBATIM unchanged",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": "Lock 4 probe (diagnosis only)",
        },
        "finish_reasons": dict(fr_all),
        "length_stops": walls,
        "responses_chars_ge_7000": near,
        "results": results,
    }
    (OUT / "probe_b3_empties.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print(f"\nfinish_reasons={dict(fr_all)} | length_stops={walls} | chars>=7000={near}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
