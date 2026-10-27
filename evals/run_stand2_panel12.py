#!/usr/bin/env python3
"""Stand-2 (iGPU, Vulkan0 = Intel Arc) panel-12 determinism runner
(prereg-stand2-igpu.md). Byte-faithful copy of the run_g1iso_panel12.py
extraction flow (g1-iso config, per-question history isolation, H5 guard)
with two additions requested by the owner's stand-2 task:

  1. REGIME CANARY (proposal v0.4, diagnostic label, not permission): before
     each pass, the 3 canary questions (311778f1, faba32e5, e47becba) run
     through the SAME g1-iso extraction flow; the fingerprint (sha256 over
     the canonical JSON of their raw extraction outputs) is recorded in the
     pass header of the artifact. FIX 2026-10-27 (owner-directed): each
     canary run uses a FRESH store (canary_p{pi}/{h}) and the raw_outputs
     are sliced per question -- the original tag canary_{h} reused the
     previous pass's store/history within one invocation and the CALLS
     filter accumulated all previous canary calls, so pass-2 fingerprints
     differed from pass-1 without any regime shift (harness defect).
  2. CONFIGURABLE PASSES via env: STAND2_PASSES (default 2) and STAND2_OUT
     (default stand2_panel12_A.json). Invocation A: passes 1-2 back-to-back
     on one llama-server instance; server restart; invocation B: pass 3 on a
     fresh instance (STAND2_PASSES=1, STAND2_OUT=stand2_panel12_B.json).
     Comparison (within A, across restart) is done by stand2_compare.py --
     this runner never compares across invocations.

Server-side determinism knobs are NOT touched by this runner: seed 42 is
pinned on the server command line, temperature 0 in the mem0 cfg.
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
STORE = f"/tmp/opencode/stand2_panel12_{int(time.time())}"
N_PASSES = int(os.environ.get("STAND2_PASSES", "2"))
OUT_NAME = os.environ.get("STAND2_OUT", "stand2_panel12_A.json")
STAND2_TAG = os.environ.get("STAND2_TAG", "A")
MAX_TOKENS = 2000  # g1 exact

PANEL8 = ["75832dbd", "0a34ad58", "1faac195", "b0479f84",
          "fca70973", "311778f1", "afdc33df", "19b5f2b3",
          "e47becba", "58bf7951", "3b6f954b", "faba32e5"]
CANARY8 = ["311778f1", "faba32e5", "e47becba"]  # proposal v0.4 composition

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


def extract_one(q, tag):
    """Full g1-iso extraction flow for one single-session question.
    raw_outputs are SLICED to the calls made by THIS extract_one call
    (harness defect fix 2026-10-27: the pass==-1 filter accumulated the
    canary CALLS of every previous pass, corrupting pass-2+ fingerprints)."""
    calls_start = len(CALLS)
    cfg = {
        "llm": {"provider": "openai", "config": {
            "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
            "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
        "embedder": {"provider": "openai", "config": {
            "model": EMB, "openai_base_url": EMBED_BASE_URL,
            "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": f"s2_{tag}", "embedding_model_dims": EMBED_DIMS,
            "path": f"{STORE}/{tag}"}},
        "history_db_path": temp_history_db(f"{STORE}/{tag}"),
        "version": "v1.1",
    }
    m = Memory.from_config(cfg)
    patch_llm_client(m, -1, -1)
    m.add(q["haystack_sessions"][0], user_id="u_stand2", infer=True)
    try:
        ga = m.get_all(filters={"user_id": "u_stand2"})
        stored = sorted(it.get("memory", "") for it in ga.get("results", ga))
    except Exception:
        stored = []
    try:
        m.vector_store.client.close()
    except Exception:
        pass
    del m
    return {"q_id": q["question_id"],
            "raw_outputs": [c["raw"] for c in CALLS[calls_start:]],
            "stored_texts": stored}


def canary_fingerprint(by8, pi):
    """Run the 3 canary questions, fingerprint = sha256 over canonical JSON
    of {q8: raw_outputs}. EACH canary run gets a FRESH store path
    (canary_p{pi}/{h}) and a fresh history db -- per-question isolation like
    the panel questions (harness defect fix 2026-10-27: the tag
    f"canary_{h}" without the pass index reused the previous pass's vector
    store and history.db within one invocation)."""
    outs = {}
    for h in CANARY8:
        r = extract_one(by8[h], f"canary_p{pi}_{h}")
        outs[h] = r["raw_outputs"]
    fp = hashlib.sha256(json.dumps(outs, sort_keys=True,
                                   ensure_ascii=False).encode()).hexdigest()
    facts = {}
    for h in CANARY8:
        n = 0
        for raw in outs[h]:
            try:
                if json.loads(raw).get("memory") is not None:
                    n += 1
            except Exception:
                pass
        facts[h] = n
    return {"canary_fp": fp, "canary_facts": facts, "canary_raw": outs}


@guarded()
def main():
    fp = announce({"runner": "evals/run_stand2_panel12.py", "max_tokens": 2000, "response_format": "json_schema strict, schema_sha256 " + SCHEMA_SHA256[:16], "add": "none", "selection": "frozen panel-12 + canary (stand-2 iGPU)", "model": MODEL, "embedder": {"model": EMB, "dims": EMBED_DIMS}, "vector_store": "qdrant, fresh store per question", "history_db": "per-question temp (isolation)", "mem0_version": "v1.1"}, LLM_BASE_URL, label=f"evals/run_stand2_panel12.py (stand2-{STAND2_TAG})")
    data = json.loads(DATA.read_text())
    by8 = {q["question_id"].split("_")[-1]: q for q in data}
    panel = [by8[h] for h in PANEL8]

    passes = []
    for pi in range(N_PASSES):
        t_pass = time.time()
        canary = canary_fingerprint(by8, pi)
        print(f"CANARY pass {pi + 1}: fp={canary['canary_fp'][:16]} "
              f"facts={canary['canary_facts']}", flush=True)
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
        passes.append({"header": {"pass": pi + 1, "canary": canary,
                                  "elapsed_s": round(time.time() - t_pass, 1)},
                       "results": results})

    per_q, ident = [], 0
    if N_PASSES >= 2:
        for qi in range(len(panel)):
            a, b = passes[0]["results"][qi], passes[1]["results"][qi]
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
            "canary": "311778f1, faba32e5, e47becba (proposal v0.4)",
            "stand": "stand-2 iGPU Vulkan0 (Intel Arc), prereg-stand2-igpu.md",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "label": f"prereg-stand2-igpu (invocation {STAND2_TAG}, passes {N_PASSES})",
        },
        "identical_questions": ident, "of": len(panel),
        "verdict_rule": "within-invocation check only (>=2 passes); the "
                        "stand-2 criterion (pass1==pass2 back-to-back; pass3 "
                        "after restart identical) is evaluated by "
                        "stand2_compare.py over both invocation artifacts",
        "per_question": per_q,
        "passes": passes,
    }
    out["provenance"].update(fp)
    (OUT / OUT_NAME).write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"STAND2 PANEL: {ident}/12 byte-identical within this invocation",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
