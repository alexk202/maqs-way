#!/usr/bin/env python3
"""(g1-probes) Diagnostic follow-ups per prereg-g1-probes.md (Обсуждение_21).

Probe A (capped-completeness, mandatory per prereg-g1 sec 3.5): 2 questions at
maxItems 60 (ONLY delta vs g1) -> expected N vs found M for the capped class.
Probe B (chunking-hypothesis, line-B mechanism test): 4 questions, session split
in half -> TWO add() calls into ONE store (second call sees Existing Memories).
NOT an eval package: diagnostic numbers only; prereg-g1 untouched; (ii) frozen.
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
from mem0 import Memory
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
OUT = Path(__file__).resolve().parent / "results"
G1_RES = OUT / "pilot_evidence_single156_g1.json"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/g1probes_{int(time.time())}"
MAX_TOKENS = 2000  # g1 exact

BASE_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "memory": {
            "type": "array", "maxItems": 31,
            "items": {
                "type": "object", "additionalProperties": False,
                "properties": {
                    "id": {"type": "string"},
                    "text": {"type": "string", "maxLength": 900},
                    "linked_memory_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10},
                },
                "required": ["id", "text"],
            },
        },
    },
    "required": ["memory"],
}


def rf_for(max_items):
    import copy
    s = copy.deepcopy(BASE_SCHEMA)
    s["properties"]["memory"]["maxItems"] = max_items
    return {"type": "json_schema", "json_schema": {"name": "g1_probe", "strict": True, "schema": s}}


PROBE_A_QIDS = ["8cf51dda", "4fd1909e"]  # loop-driven cap / clean 31-31 cap
PROBE_B_QIDS = ["8cf51dda", "cc539528", "e3fc4d6e", "4fd1909e"]  # loop x2, trunc-field, clean cap
FRAMES = []


def patch(m, tag):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        kw["response_format"] = m._probe_rf
        try:
            resp = orig(*a, **kw)
        except Exception:
            FRAMES.append({"tag": tag, "fr": "exception", "parse": "n/a", "chars": 0,
                           "facts": None, "unique_texts": None, "capped": None,
                           "facts_at_maxlen": None, "links_used": None})
            raise
        fr = "unknown"
        content = ""
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            FRAMES.append({"tag": tag, "fr": fr, "parse": "n/a", "chars": 0,
                           "facts": None, "unique_texts": None, "capped": None,
                           "facts_at_maxlen": None, "links_used": None})
            return resp
        facts = unique_texts = capped = links_used = facts_at_maxlen = None
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory") if isinstance(d, dict) else None
            if isinstance(mem, list):
                texts = [it.get("text", "") for it in mem if isinstance(it, dict)]
                facts = len(mem)
                unique_texts = len(set(texts))
                capped = (facts == m._probe_cap)
                links_used = sum(1 for it in mem
                                 if isinstance(it, dict) and it.get("linked_memory_ids"))
                facts_at_maxlen = sum(1 for s in texts if len(s) == 900)
        except Exception:
            parse = "fail"
        FRAMES.append({"tag": tag, "fr": fr, "parse": parse, "chars": len(content),
                       "facts": facts, "unique_texts": unique_texts, "capped": capped,
                       "facts_at_maxlen": facts_at_maxlen, "links_used": links_used})
        return resp

    client.chat.completions.create = wrapped


def make_mem(qi, max_items, probe_rf):
    cfg = {
        "llm": {"provider": "openai", "config": {
            "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
            "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
        "embedder": {"provider": "openai", "config": {
            "model": EMB, "openai_base_url": EMBED_BASE_URL,
            "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": f"gp_{qi}", "embedding_model_dims": EMBED_DIMS,
            "path": f"{STORE}/q{qi}"}},
        "history_db_path": temp_history_db(STORE),
        "version": "v1.1",
    }
    m = Memory.from_config(cfg)
    m._probe_rf = probe_rf
    m._probe_cap = max_items
    return m


def probe_a(by_id, g1_mem):
    out = []
    for qi, qid8 in enumerate(PROBE_A_QIDS):
        q = by_id[qid8]
        m = make_mem(f"a{qi}", 60, rf_for(60))
        patch(m, f"A:{qid8}")
        t0 = time.time()
        m.add(q["haystack_sessions"][0], user_id="u_probe", infer=True)
        el = round(time.time() - t0, 1)
        cnt = m.vector_store.client.count(f"gp_a{qi}", exact=True).count
        try: m.vector_store.client.close()
        except Exception: pass
        del m
        out.append({"q_id": qid8, "probe": "A_maxitems60", "stored": cnt,
                    "g1_stored": g1_mem.get(qid8), "ingest_s": el,
                    "frames": [f for f in FRAMES if f["tag"] == f"A:{qid8}"]})
        print(f"[A] {qid8}: stored={cnt} (g1: {g1_mem.get(qid8)}) "
              f"facts={[f['facts'] for f in out[-1]['frames']]} "
              f"unique={[f['unique_texts'] for f in out[-1]['frames']]}")
    return out


def probe_b(by_id, g1_mem):
    out = []
    for qi, qid8 in enumerate(PROBE_B_QIDS):
        q = by_id[qid8]
        sess = q["haystack_sessions"][0]
        half = len(sess) // 2
        parts = [sess[:half], sess[half:]]
        m = make_mem(f"b{qi}", 31, rf_for(31))
        t0 = time.time()
        for pi, part in enumerate(parts):
            patch(m, f"B:{qid8}:{pi+1}")
            m.add(part, user_id="u_probe", infer=True)
        el = round(time.time() - t0, 1)
        cnt = m.vector_store.client.count(f"gp_b{qi}", exact=True).count
        try: m.vector_store.client.close()
        except Exception: pass
        del m
        frames = [f for f in FRAMES if f["tag"].startswith(f"B:{qid8}")]
        out.append({"q_id": qid8, "probe": "B_chunked_half", "stored": cnt,
                    "g1_stored": g1_mem.get(qid8), "ingest_s": el,
                    "n_calls": len(parts), "frames": frames})
        print(f"[B] {qid8}: stored={cnt} (g1: {g1_mem.get(qid8)}) "
              f"facts={[f['facts'] for f in frames]} "
              f"unique={[f['unique_texts'] for f in frames]} "
              f"at900={[f['facts_at_maxlen'] for f in frames]}")
    return out


@guarded()
def main():
    data = json.loads(DATA.read_text())
    by_id = {q["question_id"][:8]: q for q in data}
    g1_mem = {}
    if G1_RES.exists():
        for r in json.loads(G1_RES.read_text())["results"]:
            g1_mem[r["q_id"][:8]] = r["memories"]

    a = probe_a(by_id, g1_mem)
    b = probe_b(by_id, g1_mem)
    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768,
            "seed": 42, "embedder": EMB, "mem0": "0724291b",
            "config": f"diagnostic probes per prereg-g1-probes.md; base g1 "
                      f"(max_tokens={MAX_TOKENS}, NO B6 prompt); Probe A: maxItems 60 (ONLY delta); "
                      f"Probe B: session split in half -> 2 adds into one store (maxItems 31)",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": "diagnostics-not-eval, prereg-g1-probes (Обсуждение_21)",
        },
        "probe_A_capped_completeness": a,
        "probe_B_chunking_hypothesis": b,
    }
    (OUT / "g1_probes.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("\nartifact: evals/results/g1_probes.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
