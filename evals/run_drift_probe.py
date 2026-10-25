#!/usr/bin/env python3
"""Drift probe (prereg-drift-probe.md, owner ТЗ 26.10): why did panel-12
shift at 2/12 after the 7-hour full-500-iso load?

Modes:
  b -- STEP B: the two shifted questions (311778f1, faba32e5), full g1-iso
       extraction flow, each twice: request cache_prompt=true / =false
       (extra_body), on the SAME FRESH server instance. Outputs compared
       across modes.
  c -- STEP C (20-min budget): replay ~100 full-500-iso extraction requests
       as prefill load (mem0 prompt builder; chunking identical to the
       runner; existing_memories for chunks 2+ parsed from the run's own
       recorded raw outputs; generation clipped to max_tokens=8 -- the cache
       cares about prefill), then the two questions again true/false.

Everything under the H5 guard; temp stores only. Artifacts:
results/drift_probe_bc.json (+ step A panel artifact saved separately by the
panel runner). Criteria are pre-registered in prereg-drift-probe.md.
"""
import hashlib
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MEM0_TELEMETRY", "False")

from isolation_guard import guarded, temp_history_db
from eval_config import (EMBED_API_KEY, EMBED_BASE_URL, EMBED_DIMS, EMBED_MODEL,
                          LLM_API_KEY, LLM_BASE_URL, LLM_MODEL)

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
F500 = Path(__file__).resolve().parent / "results/pilot_evidence_n500_iso.json"
REF = Path(__file__).resolve().parent / "results/g1iso_panel12_repro_detA.json"
OUT = Path(__file__).resolve().parent / "results"
KEY = LLM_API_KEY
MODEL = LLM_MODEL
EMB = EMBED_MODEL
STORE = f"/tmp/opencode/driftprobe_{int(time.time())}"

SHIFTED = ["311778f1", "faba32e5"]
CTX_LIMIT, CHARS_PER_TOK = 24000, 4.0

G1_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "properties": {"memory": {"type": "array", "maxItems": 31, "items": {
        "type": "object", "additionalProperties": False,
        "properties": {"id": {"type": "string"},
                      "text": {"type": "string", "maxLength": 900},
                      "linked_memory_ids": {"type": "array", "items": {"type": "string"}, "maxItems": 10}},
        "required": ["id", "text"]}}},
    "required": ["memory"],
}
G1_RF = {"type": "json_schema", "json_schema": {
    "name": "mem0_extraction_g1", "strict": True, "schema": G1_SCHEMA}}

RAW = []  # {"tag", "cache_mode", "raw"}


def patch_llm_client(m, tag, cache_mode):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        kw["response_format"] = G1_RF
        if cache_mode is not None:
            kw["extra_body"] = {"cache_prompt": cache_mode}
        resp = orig(*a, **kw)
        content = ""
        try:
            content = resp.choices[0].message.content or ""
        except Exception:
            pass
        RAW.append({"tag": tag, "cache_mode": cache_mode, "raw": content})
        return resp

    client.chat.completions.create = wrapped


def extract_question(q, tag, cache_mode):
    """Full g1-iso extraction flow for one single-session question."""
    from mem0 import Memory
    qi = SHIFTED.index(q["question_id"].split("_")[-1])
    cfg = {
        "llm": {"provider": "openai", "config": {
            "model": MODEL, "temperature": 0, "max_tokens": 2000,
            "openai_base_url": LLM_BASE_URL, "api_key": KEY}},
        "embedder": {"provider": "openai", "config": {
            "model": EMB, "openai_base_url": EMBED_BASE_URL,
            "api_key": EMBED_API_KEY, "embedding_dims": EMBED_DIMS}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": f"dp_{tag}", "embedding_model_dims": EMBED_DIMS,
            "path": f"{STORE}/{tag}"}},
        "history_db_path": temp_history_db(f"{STORE}/{tag}"),
        "version": "v1.1",
    }
    m = Memory.from_config(cfg)
    patch_llm_client(m, tag, cache_mode)
    m.add(q["haystack_sessions"][0], user_id="u_probe", infer=True)
    try:
        ga = m.get_all(filters={"user_id": "u_probe"})
        stored = sorted(it.get("memory", "") for it in ga.get("results", ga))
    except Exception:
        stored = []
    try:
        m.vector_store.client.close()
    except Exception:
        pass
    del m
    return {"tag": tag, "cache_mode": cache_mode,
            "raw": [r for r in RAW if r["tag"] == tag],
            "stored_texts": stored}


def replay_prefill(budget_s=1080, max_requests=110):
    """STEP C load: replay the first ~N full-500-iso extraction requests as
    prefill (mem0 prompt builder, run's recorded facts for chunk 2+,
    max_tokens=8, default cache). Returns request count + elapsed."""
    from openai import OpenAI
    from mem0.configs.prompts import (ADDITIVE_EXTRACTION_PROMPT,
                                      generate_additive_extraction_prompt)
    from mem0.memory.utils import parse_messages

    data = json.loads(DATA.read_text())
    art = json.loads(F500.read_text())
    cli = OpenAI(base_url=LLM_BASE_URL, api_key=KEY)
    t0, n_req, n_q = time.time(), 0, 0
    for qi, q in enumerate(data[:500]):
        if n_req >= max_requests or time.time() - t0 > budget_s:
            break
        n_q += 1
        prev_facts = []
        rec_raws = art["results"][qi]["raw_outputs"]
        for si, sess in enumerate(q["haystack_sessions"]):
            chars = sum(len(str(msg.get("content", ""))) for msg in sess)
            chunks = max(1, int(chars / (CTX_LIMIT * CHARS_PER_TOK)) + 1)
            size = max(1, len(sess) // chunks)
            for ci in range(chunks):
                part = sess[ci * size:(ci + 1) * size] if chunks > 1 else sess
                if not part:
                    continue
                if n_req >= max_requests or time.time() - t0 > budget_s:
                    break
                existing = [{"id": str(i), "text": t}
                            for i, t in enumerate(prev_facts[:10])]
                user_prompt = generate_additive_extraction_prompt(
                    existing_memories=existing,
                    new_messages=parse_messages(part),
                    last_k_messages=[])
                cli.chat.completions.create(
                    model=MODEL, temperature=0, max_tokens=8,
                    response_format={"type": "json_object"},
                    messages=[{"role": "system", "content": ADDITIVE_EXTRACTION_PROMPT},
                              {"role": "user", "content": user_prompt}])
                n_req += 1
                # next chunk of this question sees this chunk's RECORDED facts
                if ci < len(rec_raws):
                    try:
                        d = json.loads(rec_raws[ci])
                        mem = d.get("memory") if isinstance(d, dict) else None
                        if isinstance(mem, list):
                            prev_facts = [it.get("text", "") for it in mem
                                          if isinstance(it, dict) and it.get("text")]
                    except Exception:
                        pass
    return {"questions": n_q, "requests": n_req,
            "elapsed_s": round(time.time() - t0, 1)}


@guarded()
def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "b"
    data = json.loads(DATA.read_text())
    by8 = {q["question_id"].split("_")[-1]: q for q in data}
    shifted = [by8[h] for h in SHIFTED]

    if mode == "b":
        runs = {}
        for h in SHIFTED:
            q = by8[h]
            runs[h + "|true"] = extract_question(q, h + "_t", True)
            runs[h + "|false"] = extract_question(q, h + "_f", False)
        out = {"mode": "b",
               "provenance": _prov("fresh instance, no replay"),
               "runs": runs,
               "verdict": {h: runs[h + "|true"]["raw"] == runs[h + "|false"]["raw"]
                           for h in SHIFTED}}
    elif mode == "c":
        replay = replay_prefill()
        runs = {}
        for h in SHIFTED:
            q = by8[h]
            runs[h + "|true"] = extract_question(q, h + "_ct", True)
            runs[h + "|false"] = extract_question(q, h + "_cf", False)
        out = {"mode": "c", "replay": replay,
               "provenance": _prov(f"after prefill replay: {replay}"),
               "runs": runs}
    else:
        print("mode: b | c")
        return 2

    suffix = "_b" if mode == "b" else "_c"
    (OUT / f"drift_probe{suffix}.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(json.dumps({k: (v if not isinstance(v, dict) else "…")
                      for k, v in out.items()}, ensure_ascii=False)[:300])
    for k, r in out["runs"].items():
        n = len("".join(x["raw"] for x in r["raw"]))
        print(f"  {k}: raw_chars={n} stored={len(r['stored_texts'])}")
    return 0


def _prov(note):
    return {"date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "model": MODEL, "server": LLM_BASE_URL, "ctx": 32768, "seed": 42,
            "config": "g1-iso (schema 31, cap 2000) for the 2 questions; "
                      "extra_body cache_prompt true/false",
            "note": note,
            "prereg": "prereg-drift-probe.md (criteria pre-registered)"}


if __name__ == "__main__":
    sys.exit(main())
