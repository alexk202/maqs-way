#!/usr/bin/env python3
"""(g1) GRAMMAR-LAYER BASELINE: single-session slice (156 q), config = (b2) EXACTLY
(max_tokens=2000, NO B6 prompt) + ONE delta: response_format json_schema injected
into the extraction call, replacing mem0's unenforced {"type": "json_object"}.

Package (i) per council 24.10 (fork doc §11): NEUTRALITY CONTROL — grammar layer must
not break b2. NOT a fix, NOT B6. Pre-registration: evals/prereg-g1.md (signed BEFORE run).

Smoke-verified 2026-10-24 (llama-server build 9177):
  - json_object (what mem0 sends today) is NOT enforced: code fences pass through;
  - json_schema IS enforced: raw valid JSON, empty {"memory": []} allowed,
    maxItems enforced (5 facts requested -> 2 items with maxItems=2),
    token wall still reports fr=length with invalid JSON (grammar cannot save a cut).

Eval logic byte-identical to (b2) run_single156_fixcfg.py except:
  1) response_format replacement (THE grammar delta);
  2) per-call instrumentation fr/parse/chars/facts/capped/links (observation only);
  3) composition report vs b2 artifact (council §11.3) + checkpoint/artifact names.
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

from mem0 import Memory

DATA = Path("/home/aleksandr/Projects/MAQS_Way/evals/datasets/longmemeval/longmemeval_oracle.json")
OUT = Path("/home/aleksandr/Projects/MAQS_Way/evals/results")
KEY = open("/tmp/opencode/pilot8085.key").read().strip()
MODEL = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
EMB = "text-embedding-nomic-embed-text-v1.5"
STORE = f"/tmp/opencode/mem0single156g1_{int(time.time())}"
N = 156  # 70 user + 56 assistant + 30 preference
MAX_TOKENS = 2000  # b2 exact — carried from (b2), NOT from b4
B2_REF = OUT / "pilot_evidence_single156_fixcfg.json"

G1_SCHEMA = {
    "type": "object",
    "properties": {
        "memory": {
            "type": "array",
            "maxItems": 40,  # b2 natural max 39; 40 facts ~ 7200 chars ~ 1850 tok < 2000 wall
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string", "maxLength": 900},  # prompt std: 100 words ~ 700 chars
                    "linked_memory_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
                },
                "required": ["id", "text"],
            },
        },
    },
    "required": ["memory"],
}
G1_RF = {"type": "json_schema", "json_schema": {
    "name": "mem0_extraction_g1", "strict": True, "schema": G1_SCHEMA}}
SCHEMA_SHA256 = hashlib.sha256(json.dumps(G1_SCHEMA, sort_keys=True).encode()).hexdigest()
MAX_ITEMS = G1_SCHEMA["properties"]["memory"]["maxItems"]

ALL_CALLS = []  # {"q", "fr", "parse", "chars", "facts", "capped", "links_used"}


def patch_llm_client(m, qi):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        kw["response_format"] = G1_RF  # THE grammar delta: replace mem0's json_object
        try:
            resp = orig(*a, **kw)
        except Exception:
            ALL_CALLS.append({"q": qi, "fr": "exception", "parse": "n/a", "chars": 0,
                              "facts": None, "capped": None, "links_used": None})
            raise
        fr = "unknown"
        content = ""
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            ALL_CALLS.append({"q": qi, "fr": fr, "parse": "n/a", "chars": 0,
                              "facts": None, "capped": None, "links_used": None})
            return resp
        facts = capped = links_used = None
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory") if isinstance(d, dict) else None
            if isinstance(mem, list):
                facts = len(mem)
                capped = (facts == MAX_ITEMS)
                links_used = sum(1 for it in mem
                                 if isinstance(it, dict) and it.get("linked_memory_ids"))
        except Exception:
            parse = "fail"
        ALL_CALLS.append({"q": qi, "fr": fr, "parse": parse, "chars": len(content),
                          "facts": facts, "capped": capped, "links_used": links_used})
        return resp

    client.chat.completions.create = wrapped


def main():
    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant", "single-session-preference")]
    assert len(singles) == N, f"expected {N}, got {len(singles)}"

    b2_mem = {}
    if B2_REF.exists():
        for r in json.loads(B2_REF.read_text())["results"]:
            b2_mem[r["q_id"]] = (r["memories"], r["evidence_hit"])

    results = []
    for qi, q in enumerate(singles):
        cfg = {
            "llm": {"provider": "openai", "config": {
                "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
                "openai_base_url": "http://127.0.0.1:8085/v1", "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": "http://127.0.0.1:1449/v1",
                "api_key": "local-smoke", "embedding_dims": 768}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"s156g1_{qi}", "embedding_model_dims": 768,
                "path": f"{STORE}/q{qi}"}},
            "version": "v1.1",
        }
        m = Memory.from_config(cfg)
        q_calls_start = len(ALL_CALLS)
        patch_llm_client(m, qi)
        t0 = time.time()
        m.add(q["haystack_sessions"][0], user_id="u_pilot", infer=True)
        t_ing = time.time() - t0
        cnt = m.vector_store.client.count(f"s156g1_{qi}", exact=True).count
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
                {"fr": c["fr"], "parse": c["parse"], "chars": c["chars"],
                 "facts": c["facts"], "capped": c["capped"], "links_used": c["links_used"]}
                for c in q_calls
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
        (OUT / "single156_g1_partial.json").write_text(json.dumps({
            "checkpoint": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "completed": len(results), "of": N,
            "calls_total": len(ALL_CALLS),
            "results": results,
        }, indent=2, ensure_ascii=False))

    r5 = sum(1 for r in results if r["evidence_hit"]) / len(results)
    empties = sum(1 for r in results if r["memories"] == 0)
    total_calls = len(ALL_CALLS)
    fr_all = Counter(c["fr"] for c in ALL_CALLS)
    mal = sum(1 for c in ALL_CALLS if c["parse"] == "fail" and c["fr"] == "stop")
    trunc = sum(1 for c in ALL_CALLS if c["fr"] == "length")
    capped_calls = sum(1 for c in ALL_CALLS if c["capped"])
    links_total = sum(c["links_used"] or 0 for c in ALL_CALLS)
    facts_lens = sorted(c["chars"] for c in ALL_CALLS)
    total_mem = sum(r["memories"] for r in results)

    # composition report vs b2 (council §11.3): per-question flags, review list
    comp_flags = []
    for r in results:
        b2m, b2hit = b2_mem.get(r["q_id"], (None, None))
        if b2m is None:
            continue
        if (b2m > 0 and r["memories"] == 0) or (b2m and r["memories"] < 0.5 * b2m):
            comp_flags.append({"q_id": r["q_id"], "b2_mem": b2m, "g1_mem": r["memories"],
                               "b2_hit": b2hit, "g1_hit": r["evidence_hit"]})

    print(f"\nevidence-R@5 = {r5:.3f} ({sum(1 for r in results if r['evidence_hit'])}/{len(results)})")
    print(f"empty collections: {empties}/{len(results)}")
    print(f"calls (wrapped): {total_calls} | finish_reason: {dict(fr_all)}")
    print(f"mal (stop+parse-fail): {mal} | trunc (fr=length): {trunc} | capped (facts=={MAX_ITEMS}): {capped_calls}")
    print(f"total stored memories: {total_mem} (b2 ref: {sum(v[0] for v in b2_mem.values())})")
    print(f"response chars p50/p99: {facts_lens[len(facts_lens)//2]}/"
          f"{facts_lens[int(len(facts_lens)*0.99)] if len(facts_lens) > 1 else '-'}")
    print(f"links_used total (items with non-empty linked_memory_ids): {links_total}")
    print(f"composition flags vs b2 (review list): {len(comp_flags)} -> "
          f"{[f['q_id'][:8] for f in comp_flags]}")

    out = {
        "provenance": {
            "model": MODEL, "server": "http://127.0.0.1:8085/v1", "ctx": 32768,
            "seed": 42, "embedder": EMB, "mem0": "0724291b",
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "metric": "1a evidence-session R@5 + per-call grammar instrumentation",
            "selection": "single-session-156 (70 user + 56 assistant + 30 preference), committed order",
            "config": f"GRAMMAR-LAYER BASELINE (i): max_tokens={MAX_TOKENS}, NO B6 prompt "
                      f"(b2 exact) + response_format json_schema (schema sha256 {SCHEMA_SHA256[:16]}…)",
            "schema_sha256": SCHEMA_SHA256,
            "max_items": MAX_ITEMS,
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": len(results), "label": "neutrality-control-not-fix, prereg-g1",
        },
        "R_at_5_evidence": r5,
        "empty_collections": empties,
        "mal_calls": mal,
        "trunc_calls": trunc,
        "capped_calls": capped_calls,
        "calls_total": total_calls,
        "finish_reasons": dict(fr_all),
        "total_memories": total_mem,
        "links_used_total": links_total,
        "response_chars_p99": facts_lens[int(len(facts_lens) * 0.99)] if len(facts_lens) > 1 else None,
        "composition_flags_vs_b2": comp_flags,
        "results": results,
    }
    (OUT / "pilot_evidence_single156_g1.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
