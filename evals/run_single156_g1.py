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
Amend-1 (review-driven, pre-run): schema maxItems 40->31 (measured budget),
additionalProperties:false, frame fields unique_texts/facts_at_900, mal = parse-fail
at ANY fr except length, other_fail = exception/unknown, loop = facts >= 2*unique_texts,
mirror composition flag g1 > 120% b2. Prereg: evals/prereg-g1.md + prereg-g1-amend-1.md.
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

from isolation_guard import guarded, temp_history_db
from config_fingerprint import announce
from mem0 import Memory
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/mem0single156g1_{int(time.time())}"
N = 156  # 70 user + 56 assistant + 30 preference
MAX_TOKENS = 2000  # b2 exact — carried from (b2), NOT from b4
B2_REF = OUT / "pilot_evidence_single156_fixcfg.json"

G1_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "memory": {
            "type": "array",
            # amend-1: floor(1800 tok * 4.0 chars/tok / (190 avg + 40 json overhead)) = 31
            "maxItems": 31,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string", "maxLength": 900},  # measured max 435, prompt std ~700
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
        facts = capped = links_used = unique_texts = facts_at_maxlen = max_fact_chars = None
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory") if isinstance(d, dict) else None
            if isinstance(mem, list):
                texts = [it.get("text", "") for it in mem if isinstance(it, dict)]
                facts = len(mem)
                capped = (facts == MAX_ITEMS)
                links_used = sum(1 for it in mem
                                 if isinstance(it, dict) and it.get("linked_memory_ids"))
                unique_texts = len(set(texts))
                facts_at_maxlen = sum(1 for s in texts if len(s) == 900)
                max_fact_chars = max((len(s) for s in texts), default=0)
        except Exception:
            parse = "fail"
        ALL_CALLS.append({"q": qi, "fr": fr, "parse": parse, "chars": len(content),
                          "facts": facts, "capped": capped, "links_used": links_used,
                          "unique_texts": unique_texts, "facts_at_maxlen": facts_at_maxlen,
                          "max_fact_chars": max_fact_chars})
        return resp

    client.chat.completions.create = wrapped


@guarded()
def main():
    fp = announce({"runner": "evals/run_single156_g1.py", "max_tokens": 2000, "response_format": "json_schema strict, schema_sha256 " + SCHEMA_SHA256[:16], "add": "none", "selection": "single-156 committed order", "model": MODEL, "embedder": {"model": EMB, "dims": EMBED_DIMS}, "vector_store": "qdrant, fresh store per question", "history_db": "per-question temp (isolation)", "mem0_version": "v1.1"}, LLM_BASE_URL, label="evals/run_single156_g1.py")
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
                "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
            "embedder": {"provider": "openai", "config": {
                "model": EMB, "openai_base_url": EMBED_BASE_URL,
                "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
            "vector_store": {"provider": "qdrant", "config": {
                "collection_name": f"s156g1_{qi}", "embedding_model_dims": EMBED_DIMS,
                "path": f"{STORE}/q{qi}"}},
            "history_db_path": temp_history_db(f"{STORE}/q{qi}"),
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
                 "facts": c["facts"], "capped": c["capped"], "links_used": c["links_used"],
                 "unique_texts": c["unique_texts"], "facts_at_maxlen": c["facts_at_maxlen"],
                 "max_fact_chars": c["max_fact_chars"]}
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
    # amend-1: mal = parse fail at ANY fr except length; other_fail = exception/unknown
    mal = sum(1 for c in ALL_CALLS if c["parse"] == "fail" and c["fr"] != "length")
    other_fail = sum(1 for c in ALL_CALLS if c["fr"] in ("exception", "unknown"))
    trunc = sum(1 for c in ALL_CALLS if c["fr"] == "length")
    capped_calls = sum(1 for c in ALL_CALLS if c["capped"])
    loop_calls = sum(1 for c in ALL_CALLS
                    if c["facts"] is not None and c["unique_texts"] is not None
                    and c["facts"] >= 2 * c["unique_texts"])
    facts_at_maxlen_total = sum(c["facts_at_maxlen"] or 0 for c in ALL_CALLS)
    links_total = sum(c["links_used"] or 0 for c in ALL_CALLS)
    facts_lens = sorted(c["chars"] for c in ALL_CALLS)
    total_mem = sum(r["memories"] for r in results)

    # composition report vs b2 (council §11.3 + amend-1 mirror): per-question flags
    comp_flags = []
    for r in results:
        b2m, b2hit = b2_mem.get(r["q_id"], (None, None))
        if b2m is None:
            continue
        if (b2m > 0 and r["memories"] == 0) or (b2m and r["memories"] < 0.5 * b2m) \
                or (b2m and r["memories"] > 1.2 * b2m):
            comp_flags.append({"q_id": r["q_id"], "b2_mem": b2m, "g1_mem": r["memories"],
                               "b2_hit": b2hit, "g1_hit": r["evidence_hit"]})

    print(f"\nevidence-R@5 = {r5:.3f} ({sum(1 for r in results if r['evidence_hit'])}/{len(results)})")
    print(f"empty collections: {empties}/{len(results)}")
    print(f"calls (wrapped): {total_calls} | finish_reason: {dict(fr_all)}")
    print(f"mal (parse-fail@any-fr-except-length): {mal} | other_fail: {other_fail} | "
          f"trunc (fr=length): {trunc} | capped (facts=={MAX_ITEMS}): {capped_calls}")
    print(f"loop frames (facts>=2x unique): {loop_calls} | facts at 900 (trunc-field): {facts_at_maxlen_total}")
    print(f"total stored memories: {total_mem} (b2 ref: {sum(v[0] for v in b2_mem.values())})")
    print(f"response chars p50/p99: {facts_lens[len(facts_lens)//2]}/"
          f"{facts_lens[int(len(facts_lens)*0.99)] if len(facts_lens) > 1 else '-'}")
    print(f"links_used total (items with non-empty linked_memory_ids): {links_total}")
    print(f"composition flags vs b2 (review list): {len(comp_flags)} -> "
          f"{[f['q_id'][:8] for f in comp_flags]}")

    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768,
            "seed": 42, "embedder": EMB, "mem0": "0724291b",
            "dataset": "xiaowu0162/longmemeval-cleaned longmemeval_oracle.json",
            "metric": "1a evidence-session R@5 + per-call grammar instrumentation",
            "selection": "single-session-156 (70 user + 56 assistant + 30 preference), committed order",
            "config": f"GRAMMAR-LAYER BASELINE (i): max_tokens={MAX_TOKENS}, NO B6 prompt "
                      f"(b2 exact) + response_format json_schema (schema sha256 {SCHEMA_SHA256[:16]}…)",
            "schema_sha256": SCHEMA_SHA256,
            "max_items": MAX_ITEMS,
            "amend": "prereg-g1-amend-1 (maxItems 31, additionalProperties false, "
                     "loop/trunc-field guards, mirror flags, mal wording)",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "n": len(results), "label": "neutrality-control-not-fix, prereg-g1",
        },
        "R_at_5_evidence": r5,
        "empty_collections": empties,
        "mal_calls": mal,
        "other_fail_calls": other_fail,
        "trunc_calls": trunc,
        "capped_calls": capped_calls,
        "loop_calls": loop_calls,
        "facts_at_maxlen_total": facts_at_maxlen_total,
        "calls_total": total_calls,
        "finish_reasons": dict(fr_all),
        "total_memories": total_mem,
        "links_used_total": links_total,
        "response_chars_p99": facts_lens[int(len(facts_lens) * 0.99)] if len(facts_lens) > 1 else None,
        "composition_flags_vs_b2": comp_flags,
        "results": results,
    }
    out["provenance"].update(fp)
    (OUT / "pilot_evidence_single156_g1.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
