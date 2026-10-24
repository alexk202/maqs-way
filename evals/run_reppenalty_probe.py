#!/usr/bin/env python3
"""(rep-penalty probe) Diagnostic per prereg-reppenalty-probe.md (council 5/5, pre-(ii)).

Key pre-fact (verified via /props): build 9177 default repeat_penalty = 1.0 (DISABLED)
-> all branch runs went WITHOUT penalty; loop arose at 1.0; name-loss baseline 0.168
measured at 1.0. This probe tests: {1.1, 1.2, 1.3} on 2 loop questions (does penalty
kill the loop?) + 2 entity-rich questions (does penalty hurt names?). Criteria
hardcoded in the prereg BEFORE the run. NOT an eval package.
"""
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("MEM0_TELEMETRY", "False")

from mem0 import Memory
from qdrant_client import QdrantClient

DATA = Path("/home/aleksandr/Projects/MAQS_Way/evals/datasets/longmemeval/longmemeval_oracle.json")
OUT = Path("/home/aleksandr/Projects/MAQS_Way/evals/results")
G1_RES = OUT / "pilot_evidence_single156_g1.json"
V11_RES = OUT / "verbatim_g1_v11.json"
KEY = open("/tmp/opencode/pilot8085.key").read().strip()
MODEL = "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf"
EMB = "text-embedding-nomic-embed-text-v1.5"
STORE = f"/tmp/opencode/reppenalty_{int(time.time())}"
PENALTIES = [1.1, 1.2, 1.3]
LOOP_QIDS = ["8cf51dda", "cc539528"]
ENTITY_QIDS = ["75832dbd", "0a34ad58"]

G1_SCHEMA = {
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
G1_RF = {"type": "json_schema", "json_schema": {"name": "g1_probe", "strict": True, "schema": G1_SCHEMA}}

DQ = re.compile(r'"([^"\n]{3,80})"')
CQ = re.compile(r"\u201c([^\u201d\n]{3,80})\u201d")
TITLE = re.compile(r"\b(?:[A-Z][\w-]*\s+){1,5}[A-Z][\w-]*\b")
STOP_SUBSTR = ("http", "www.", "@")
UI_BLOCKLIST = {"summary", "share", "tickets", "story", "freeze", "hanger", "provenance",
                "notable events", "purchase price", "dome date", "graduated", "pursued",
                "currently reading", "style inspiration", "fashion diary",
                "speaking of relationships", "acquisition date", "notes"}

FRAMES = []


def patch(m, tag, penalty):
    client = m.llm.client
    orig = client.chat.completions.create

    def wrapped(*a, **kw):
        kw["response_format"] = G1_RF
        kw["repeat_penalty"] = penalty  # THE probe delta
        try:
            resp = orig(*a, **kw)
        except Exception:
            FRAMES.append({"tag": tag, "fr": "exception", "parse": "n/a", "chars": 0,
                           "facts": None, "unique": None})
            raise
        fr = "unknown"
        content = ""
        try:
            fr = resp.choices[0].finish_reason
            content = resp.choices[0].message.content or ""
        except Exception:
            FRAMES.append({"tag": tag, "fr": fr, "parse": "n/a", "chars": 0,
                           "facts": None, "unique": None})
            return resp
        facts = unique = None
        try:
            d = json.loads(content)
            parse = "ok"
            mem = d.get("memory", []) if isinstance(d, dict) else []
            texts = [it.get("text", "") for it in mem if isinstance(it, dict)]
            facts = len(mem)
            unique = len(set(texts))
        except Exception:
            parse = "fail"
        FRAMES.append({"tag": tag, "fr": fr, "parse": parse, "chars": len(content),
                       "facts": facts, "unique": unique, "texts": texts if parse == "ok" else []})
        return resp

    client.chat.completions.create = wrapped


def run_q(q, tag, penalty, qi):
    cfg = {
        "llm": {"provider": "openai", "config": {
            "model": MODEL, "temperature": 0, "max_tokens": 2000,
            "openai_base_url": "http://127.0.0.1:8085/v1", "api_key": KEY}},
        "embedder": {"provider": "openai", "config": {
            "model": EMB, "openai_base_url": "http://127.0.0.1:1449/v1",
            "api_key": "local-smoke", "embedding_dims": 768}},
        "vector_store": {"provider": "qdrant", "config": {
            "collection_name": f"rp_{qi}", "embedding_model_dims": 768,
            "path": f"{STORE}/q{qi}"}},
        "version": "v1.1",
    }
    m = Memory.from_config(cfg)
    patch(m, tag, penalty)
    t0 = time.time()
    m.add(q["haystack_sessions"][0], user_id="u_probe", infer=True)
    el = round(time.time() - t0, 1)
    texts = []
    for f in FRAMES:
        if f["tag"] == tag and f.get("texts"):
            texts = f["texts"]
    cnt = m.vector_store.client.count(f"rp_{qi}", exact=True).count
    try:
        m.vector_store.client.close()
    except Exception:
        pass
    del m
    return {"tag": tag, "stored": cnt, "ingest_s": el,
            "frames": [{k: v for k, v in f.items() if k != "texts"}
                       for f in FRAMES if f["tag"] == tag],
            "texts": texts}


def entity_recall(q, texts):
    sess_text = "\n".join(str(mm.get("content", "")) for mm in q["haystack_sessions"][0])
    quoted = {mm.group(1).strip().strip(",.;:!?") for rx in (DQ, CQ) for mm in rx.finditer(sess_text)}
    titles = {mm.group(0).strip().strip(",.;:!?") for mm in TITLE.finditer(sess_text)}
    items = set()
    for i in list(quoted) + list(titles):
        if not any(s in i.lower() for s in STOP_SUBSTR) and \
           not any(i.lower() == b or i.lower().rstrip(",.") == b for b in UI_BLOCKLIST):
            items.add(i)
    if not items:
        return None
    blob = re.sub(r"\s+", " ", re.sub(r"[^\w\s%$.]", " ", " ".join(texts)).strip().lower())
    miss = sum(1 for i in items if re.sub(r"\s+", " ", re.sub(r"[^\w\s%$.]", " ", i).strip().lower()) not in blob)
    return {"n": len(items), "kept": len(items) - miss,
            "recall": round(1 - miss / len(items), 3)}


def main():
    data = json.loads(DATA.read_text())
    by_id8 = {}
    for q in data:
        by_id8.setdefault(q["question_id"][:8], []).append(q)
    g1 = {r["q_id"][:8]: r for r in json.loads(G1_RES.read_text())["results"]}
    v11 = {r["q_id"]: r for r in json.loads(V11_RES.read_text())["per_question"]}

    results = []
    qi = 0
    for qid8 in LOOP_QIDS + ENTITY_QIDS:
        q = by_id8[qid8][0]
        for p in PENALTIES:
            qi += 1
            r = run_q(q, f"{qid8}@{p}", p, qi)
            r["q_id8"] = qid8
            r["penalty"] = p
            if qid8 in ENTITY_QIDS and r["texts"]:
                r["entity_recall"] = entity_recall(q, r["texts"])
            results.append(r)
            loopf = any(f.get("facts") is not None and f.get("unique") is not None and
                        f["facts"] >= 2 * f["unique"] for f in r["frames"])
            er = r.get("entity_recall")
            print(f"[{qid8}@{p}] stored={r['stored']} facts={[f.get('facts') for f in r['frames']]} "
                  f"unique={[f.get('unique') for f in r['frames']]} loop={loopf} "
                  f"recall={er['recall'] if er else '-'}")

    out = {
        "provenance": {
            "label": "diagnostic probe per prereg-reppenalty-probe.md; criteria pre-fixed",
            "server_default_repeat_penalty": 1.0,
            "note": "all branch runs (b2..g1) executed with penalty DISABLED (1.0)",
            "penalties_tested": PENALTIES,
            "baseline_p1.0": {qid8: {"stored": g1[qid8]["memories"],
                                      "v11_recall": v11.get(qid8, {}).get("entity_recall_norm")}
                              for qid8 in LOOP_QIDS + ENTITY_QIDS},
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "results": results,
    }
    (OUT / "reppenalty_probe.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("\nartifact: evals/results/reppenalty_probe.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
