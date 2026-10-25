#!/usr/bin/env python3
"""g1-iso ATTRACTOR determinism check (owner-sanctioned follow-up, 2026-10-25).

The panel-12 determinism experiment showed byte-identity within AND across
server instances -- but the frozen pair-panel EXCLUDES the metastable attractor
questions by design, so it could not see the g1 vs g1-iso-a class drift. This
runner probes exactly that subset: the six loop/comp-failure questions excluded
from the verbatim panel (8cf51dda, cc539528, 118b2229, 853b0a1d, e8a79c70,
e48988bc), the clean-capped question (4fd1909e), plus two byte-stable controls
from the frozen panel (75832dbd, e47becba). Config identical to g1-iso-b
(per-question history isolation, schema 31, cap 2000, T=0, server seed 42);
TWO passes per invocation, raw extraction outputs dumped for byte-comparison;
run once per server instance, compare within and ACROSS instances.
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
STORE = f"/tmp/opencode/g1iso_attr_{int(time.time())}"
N_PASSES = 2
MAX_TOKENS = 2000  # g1 exact

# kind: attractor = excluded from the frozen panel as loop/comp-failure (or
# clean-capped); control = byte-stable panel member
QSET = [("8cf51dda", "attractor_loop"), ("cc539528", "attractor_loop"),
        ("118b2229", "attractor_compfail"), ("853b0a1d", "attractor_compfail"),
        ("e8a79c70", "attractor_compfail"), ("e48988bc", "attractor_compfail"),
        ("4fd1909e", "attractor_capped_clean"),
        ("75832dbd", "control_stable"), ("e47becba", "control_stable")]

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

CALLS = []


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
        facts = capped = unique = None
        parse = "n/a"
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory") if isinstance(d, dict) else None
            if isinstance(mem, list):
                texts = [it.get("text", "") for it in mem if isinstance(it, dict)]
                facts = len(mem)
                capped = (facts == MAX_ITEMS)
                unique = len(set(texts))
        except Exception:
            parse = "fail"
        CALLS.append({"pass": pi, "qi": qi, "fr": fr, "parse": parse,
                      "chars": len(content), "facts": facts, "capped": capped,
                      "unique": unique, "raw": content})
        return resp

    client.chat.completions.create = wrapped


@guarded()
def main():
    data = json.loads(DATA.read_text())
    by8 = {q["question_id"].split("_")[-1]: q for q in data}
    panel = [(by8[h], kind) for h, kind in QSET]
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant",
                "single-session-preference")]
    sset = {q["question_id"] for q in singles}
    for q, _ in panel:
        assert q["question_id"] in sset, f"{q['question_id']} not a single-session question"

    passes = []
    for pi in range(N_PASSES):
        results = []
        for qi, (q, kind) in enumerate(panel):
            calls_start = len(CALLS)
            cfg = {
                "llm": {"provider": "openai", "config": {
                    "model": MODEL, "temperature": 0, "max_tokens": MAX_TOKENS,
                    "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
                "embedder": {"provider": "openai", "config": {
                    "model": EMB, "openai_base_url": EMBED_BASE_URL,
                    "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
                "vector_store": {"provider": "qdrant", "config": {
                    "collection_name": f"attr_{pi}_{qi}", "embedding_model_dims": EMBED_DIMS,
                    "path": f"{STORE}/pass{pi}/q{qi}"}},
                "history_db_path": temp_history_db(f"{STORE}/pass{pi}/q{qi}"),
                "version": "v1.1",
            }
            m = Memory.from_config(cfg)
            patch_llm_client(m, pi, qi)
            t0 = time.time()
            m.add(q["haystack_sessions"][0], user_id="u_attr", infer=True)
            t_ing = time.time() - t0
            try:
                ga = m.get_all(filters={"user_id": "u_attr"})
                stored = sorted(it.get("memory", "") for it in ga.get("results", ga))
            except Exception:
                stored = []
            qcalls = CALLS[calls_start:]
            results.append({
                "q_id": q["question_id"], "kind": kind,
                "frames": [{k: c[k] for k in ("fr", "parse", "chars", "facts",
                                              "capped", "unique")} for c in qcalls],
                "raw_outputs": [c["raw"] for c in qcalls],
                "stored_texts": stored,
                "ingest_s": round(t_ing, 1),
            })
            print(f"[pass {pi + 1}/{N_PASSES}][{qi + 1}/{len(panel)}] "
                  f"{q['question_id'][:12]} ({kind}) calls={len(qcalls)} "
                  f"ingest={t_ing:.0f}s facts={[c['facts'] for c in qcalls]}", flush=True)
            try:
                m.vector_store.client.close()
            except Exception:
                pass
            del m
        passes.append(results)

    per_q, ident_all, ident_attr, ident_ctrl = [], 0, 0, 0
    for qi, (q, kind) in enumerate(panel):
        a, b = passes[0][qi], passes[1][qi]
        raw_eq = a["raw_outputs"] == b["raw_outputs"]
        st_eq = a["stored_texts"] == b["stored_texts"]
        fr_eq = a["frames"] == b["frames"]
        ok = raw_eq and st_eq and fr_eq
        ident_all += ok
        if kind.startswith("control"):
            ident_ctrl += ok
        else:
            ident_attr += ok
        per_q.append({"q_id": a["q_id"], "kind": kind, "raw_identical": raw_eq,
                      "stored_identical": st_eq, "frames_identical": fr_eq,
                      "byte_identical": ok,
                      "facts_p1": [f["facts"] for f in a["frames"]],
                      "facts_p2": [f["facts"] for f in b["frames"]],
                      "unique_p1": [f["unique"] for f in a["frames"]],
                      "unique_p2": [f["unique"] for f in b["frames"]]})

    out = {
        "provenance": {
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768, "seed": 42,
            "schema_sha256": SCHEMA_SHA256, "max_items": MAX_ITEMS,
            "max_tokens": MAX_TOKENS, "repeat_penalty": 1.0,
            "isolation": "per-question history (g1-iso-b config)",
            "date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "label": "attractor determinism check (owner-sanctioned follow-up)",
            "question_set": [{"q8": h, "kind": k} for h, k in QSET],
        },
        "identical_all": ident_all, "of": len(panel),
        "identical_attractors": ident_attr, "of_attractors": len(panel) - 2,
        "identical_controls": ident_ctrl, "of_controls": 2,
        "per_question": per_q,
        "passes": passes,
    }
    (OUT / "g1iso_attractors_repro.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"ATTRACTORS REPRO (within-instance): all {ident_all}/{len(panel)}, "
          f"attractors {ident_attr}/{len(panel) - 2}, controls {ident_ctrl}/2",
          flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
