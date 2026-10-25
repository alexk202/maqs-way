#!/usr/bin/env python3
"""g1-iso panel reproducibility runner (prereg-g1-iso.md part B, DRAFT for signature).

Frozen 12-question panel (verbatim_g1_v12) run TWICE back-to-back under the
g1-iso config (the ONE delta vs frozen g1: history_db_path -> temp store; already
in ffb5879). Seed 42 pinned on the server. Captures RAW extraction outputs per
wrapped call so the byte-identity criterion of the prereg is checkable from the
artifact alone. Instrumentation (raw dump, panel slice, x2 passes) changes
nothing in the extraction config; H5 guard active as in every runner.
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
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/g1iso_panel12_{int(time.time())}"
N_PASSES = 2
MAX_TOKENS = 2000  # g1 exact

PANEL8 = ["75832dbd", "0a34ad58", "1faac195", "b0479f84",
          "fca70973", "311778f1", "afdc33df", "19b5f2b3",
          "e47becba", "58bf7951", "3b6f954b", "faba32e5"]

G1_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {
        "memory": {
            "type": "array",
            "maxItems": 31,
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
G1_RF = {"type": "json_schema", "json_schema": {
    "name": "mem0_extraction_g1", "strict": True, "schema": G1_SCHEMA}}
SCHEMA_SHA256 = hashlib.sha256(json.dumps(G1_SCHEMA, sort_keys=True).encode()).hexdigest()
MAX_ITEMS = G1_SCHEMA["properties"]["memory"]["maxItems"]

CALLS = []  # {"pass", "qi", "fr", "parse", "chars", "facts", "capped", "raw"}


def patch_llm_client(m, pi, qi):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        kw["response_format"] = G1_RF
        resp = orig(*a, **kw)
        fr, content = "unknown", ""
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            pass
        facts = capped = None
        parse = "n/a"
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory") if isinstance(d, dict) else None
            if isinstance(mem, list):
                facts = len(mem)
                capped = (facts == MAX_ITEMS)
        except Exception:
            parse = "fail"
        CALLS.append({"pass": pi, "qi": qi, "fr": fr, "parse": parse,
                      "chars": len(content), "facts": facts, "capped": capped,
                      "raw": content})
        return resp

    client.chat.completions.create = wrapped


@guarded()
def main():
    data = json.loads(DATA.read_text())
    by8 = {q["question_id"].split("_")[-1]: q for q in data}
    panel = [by8[h] for h in PANEL8]

    passes = []
    for pi in range(N_PASSES):
        results = []
        for qi, q in enumerate(panel):
            calls_start = len(CALLS)
            cfg = {
                "llm": {"provider": "openai", "config": {
                    "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
                    "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
                "embedder": {"provider": "openai", "config": {
                    "model": EMB, "openai_base_url": EMBED_BASE_URL,
                    "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
                "vector_store": {"provider": "qdrant", "config": {
                    "collection_name": f"p12_{pi}_{qi}", "embedding_model_dims": EMBED_DIMS,
                    "path": f"{STORE}/pass{pi}/q{qi}"}},
                "history_db_path": temp_history_db(f"{STORE}/pass{pi}/q{qi}"),
                "version": "v1.1",
            }
            m = Memory.from_config(cfg)
            patch_llm_client(m, pi, qi)
            t0 = time.time()
            m.add(q["haystack_sessions"][0], user_id="u_pilot", infer=True)
            t_ing = time.time() - t0
            res = m.search(q["question"], filters={"user_id": "u_pilot"}, top_k=5)
            items = res.get("results", res) if isinstance(res, dict) else res
            top5 = [(it.get("id"), it.get("memory", "")) for it in items]
            ans_sess = set(q["answer_session_ids"])
            sess_of_add = q["haystack_session_ids"][0]
            ev_hit = any(sess_of_add in ans_sess for _, _ in top5)
            qcalls = CALLS[calls_start:]
            try:
                ga = m.get_all(filters={"user_id": "u_pilot"})
                stored = sorted(it.get("memory", "") for it in ga.get("results", ga))
            except Exception:
                stored = []
            results.append({
                "q_id": q["question_id"],
                "frames": [{k: c[k] for k in ("fr", "parse", "chars", "facts", "capped")}
                           for c in qcalls],
                "raw_outputs": [c["raw"] for c in qcalls],
                "memory_texts": sorted(t or "" for _, t in top5),
                "stored_texts": stored,
                "evidence_hit": ev_hit, "ingest_s": round(t_ing, 1),
            })
            print(f"[pass {pi + 1}/{N_PASSES}][{qi + 1}/12] {q['question_id'][:12]} "
                  f"ev={ev_hit} calls={len(qcalls)} ingest={t_ing:.0f}s", flush=True)
            try:
                m.vector_store.client.close()
            except Exception:
                pass
            del m
        passes.append(results)

    per_q, ident = [], 0
    for qi in range(len(panel)):
        a, b = passes[0][qi], passes[1][qi]
        raw_eq = a["raw_outputs"] == b["raw_outputs"]
        mem_eq = a["memory_texts"] == b["memory_texts"]
        st_eq = a["stored_texts"] == b["stored_texts"]
        fr_eq = a["frames"] == b["frames"]
        ok = raw_eq and mem_eq and st_eq and fr_eq
        ident += ok
        per_q.append({"q_id": a["q_id"], "raw_identical": raw_eq,
                      "memory_texts_identical": mem_eq,
                      "stored_texts_identical": st_eq,
                      "frames_identical": fr_eq,
                      "byte_identical": ok})

    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768, "seed": 42,
            "embedder": EMB, "mem0": "0724291b",
            "schema_sha256": SCHEMA_SHA256, "max_items": MAX_ITEMS,
            "max_tokens": MAX_TOKENS, "repeat_penalty": 1.0,
            "delta_vs_g1": "history_db_path -> temp store (H5, ffb5879)",
            "panel": "frozen verbatim_g1_v12 12 ids (4/4/4)",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": "prereg-g1-iso part B (draft->signed->run)",
        },
        "identical_questions": ident, "of": len(panel),
        "verdict_rule": "all 12 byte-identical -> history tail was the run-to-run "
                        "variance source (pinned seed); any difference -> GPU "
                        "nondeterminism remains; unpinned-seed era unexplained by this",
        "per_question": per_q,
        "passes": passes,
    }
    (OUT / "g1iso_panel12_repro.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"PANEL REPRO: {ident}/12 byte-identical", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
