#!/usr/bin/env python3
"""Rank diagnostic per council round: misses to END of haystack + hit fragility.

1. Hits (496): distribution of first-evidence rank (1..5) from stored top5 —
   fragility check (many hits at rank 5 = 0.992 on the edge).
2. Random 15 hits (seed 42): their first-evidence ranks.
3. Misses (4): FULL ranking of the question's collection (all extracted
   memories — oracle mode keeps only 7-31 facts per question), find first
   memory containing the answer substring → rank, or ABSENT (= extraction
   never produced an answer-bearing fact — a mode outside the council's table).
CPU only (embedder :1449 nomic + qdrant local).
"""
import glob
import json
import random
import sys
import urllib.request
from pathlib import Path

from qdrant_client import QdrantClient

DATA = Path("/home/aleksandr/Projects/MAQS_Way/evals/datasets/longmemeval/longmemeval_oracle.json")
RESULTS = Path("/home/aleksandr/Projects/MAQS_Way/evals/results/pilot_evidence_n500.json")
STORE = sorted(glob.glob("/tmp/opencode/mem0ev_*"))[-1]
EMB = "http://127.0.0.1:1449/v1/embeddings"


def embed(text):
    body = json.dumps({"model": "text-embedding-nomic-embed-text-v1.5",
                       "input": text}).encode()
    req = urllib.request.Request(EMB, data=body, headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=30))["data"][0]["embedding"]


def main():
    data = json.loads(DATA.read_text())
    by_qid = {q["question_id"]: q for q in data}
    d = json.loads(RESULTS.read_text())
    res = d["results"]

    # --- 1. hit fragility: first-evidence rank distribution ---
    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for r in res:
        if not r["evidence_hit"]:
            continue
        ans_sess = set(by_qid[r["q_id"]]["answer_session_ids"])
        for i, t in enumerate(r["top5"]):
            if any(s in ans_sess for s in t["sessions"]):
                dist[i + 1] += 1
                break
    total_hits = sum(dist.values())
    print(f"== HIT first-evidence rank distribution (n={total_hits}) ==")
    for k in sorted(dist):
        print(f"  rank {k}: {dist[k]:4d} ({dist[k]/total_hits*100:.1f}%)")
    edge = dist[4] + dist[5]
    print(f"  at-edge (4-5): {edge} ({edge/total_hits*100:.1f}%) — fragility signal if high")

    # --- 2. random 15 hits (seed 42) ---
    hits = [r for r in res if r["evidence_hit"]]
    random.seed(42)
    sample = random.sample(hits, 15)
    print("\n== RANDOM 15 HITS (seed 42): first-evidence rank ==")
    for r in sample:
        ans_sess = set(by_qid[r["q_id"]]["answer_session_ids"])
        rank = next((i + 1 for i, t in enumerate(r["top5"])
                     if any(s in ans_sess for s in t["sessions"])), None)
        print(f"  {r['q_id'][:8]} {r['q_type'][:24]:24s} rank={rank}")

    # --- 3. misses: full ranking, answer-substring rank ---
    print("\n== 4 MISSES: FULL RANKING (all extracted memories) ==")
    misses = [r for r in res if not r["evidence_hit"]]
    for r in misses:
        q = by_qid[r["q_id"]]
        qi = res.index(r)
        coll = f"ev_{qi}"
        c = QdrantClient(path=f"{STORE}/q{qi}")
        cnt = c.count(coll, exact=True).count
        if cnt == 0:
            print(f"  {r['q_id'][:8]} {r['q_type'][:24]:24s} answer={str(q['answer'])[:30]!r:32s} "
                  f"-> COLLECTION EMPTY (0 memories)  (EXTRACTION-side absence)")
            continue
        vec = embed(q["question"])
        # scroll ALL points with payload, then rank by vector search over all
        points = c.query_points(coll, query=vec, limit=cnt, with_payload=True).points
        ans = str(q["answer"]).strip().lower()
        found = None
        for rank, p in enumerate(points, 1):
            txt = str(p.payload.get("data", "")).lower()
            if ans in txt:
                found = rank
                break
        if found:
            print(f"  {r['q_id'][:8]} {r['q_type'][:24]:24s} answer={ans[:30]!r:32s} "
                  f"-> rank {found}/{cnt}  (RANKING zone 6-30)")
        else:
            print(f"  {r['q_id'][:8]} {r['q_type'][:24]:24s} answer={ans[:30]!r:32s} "
                  f"-> ABSENT in all {cnt} memories  (EXTRACTION-side absence)")
    print("\nNote: oracle collections hold 7-31 extracted facts, so rank scale is 1..~31;")
    print("the council's '>50/100' bracket cannot occur — the real split is RANKING (6-31) vs EXTRACTION-ABSENT.")


if __name__ == "__main__":
    sys.exit(main())