#!/usr/bin/env python3
"""(verbatim v0) Posthoc-exploratory diagnostic per council proposal (Обсуждение_21):
R@5 is saturated (1.000) and blind to the B6 class (title lost in paraphrase).
This measures VERBATIM PRESERVATION directly: extract quoted titles + numbers from
each question's source session, check literal presence in the stored memory texts.

g1 stores only (b2 stores wiped with /tmp on the Oct reboot) -> standalone baseline;
informative for the fork: high quoted-recall -> B6-class likely absent in g1;
low recall + visible paraphrase in worst cases -> B6-class alive -> (ii) has a
purpose ONLY with this metric (not R@5). NOT a prereg'd guard; label: posthoc.
"""
import json
import re
from pathlib import Path

from qdrant_client import QdrantClient

DATA = Path("/home/aleksandr/Projects/MAQS_Way/evals/datasets/longmemeval/longmemeval_oracle.json")
G1_RES = Path("/home/aleksandr/Projects/MAQS_Way/evals/results/pilot_evidence_single156_g1.json")
OUT = Path("/home/aleksandr/Projects/MAQS_Way/evals/results")

DQ = re.compile(r'"([^"\n]{3,80})"')            # straight double quotes
CQ = re.compile(r"\u201c([^\u201d\n]{3,80})\u201d")  # curly quotes
NUM = re.compile(r"(?<![\w.])\d[\d,.]*\d(?![\w.])|(?<![\w.])\d(?![\w.])")

STOP_SUBSTR = ("http", "www.", "@")  # noise guards for quoted spans


def source_items(text):
    quoted = set(m.group(1).strip() for rx in (DQ, CQ) for m in rx.finditer(text))
    quoted = {q for q in quoted if not any(s in q.lower() for s in STOP_SUBSTR)}
    nums = set(m.group(0) for m in NUM.finditer(text))
    return quoted, nums


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def main():
    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant", "single-session-preference")]
    g1 = json.loads(G1_RES.read_text())["results"]
    assert len(singles) == len(g1) == 156

    store_root = None
    import glob
    cands = sorted(glob.glob("/tmp/opencode/mem0single156g1_*"))
    assert cands, "g1 store dir not found"
    store_root = cands[-1]

    per_q = []
    for qi, (q, g1r) in enumerate(zip(singles, g1)):
        sess_text = "\n".join(str(m.get("content", "")) for m in q["haystack_sessions"][0])
        quoted, nums = source_items(sess_text)
        client = QdrantClient(path=f"{store_root}/q{qi}")
        pts, _ = client.scroll(collection_name=f"s156g1_{qi}", limit=100,
                               with_payload=True, with_vectors=False)
        client.close()
        stored_blob = norm(" ".join(r.payload.get("data", "") for r in pts))
        q_miss, n_miss = [], []
        for item in quoted:
            if norm(item) not in stored_blob:
                q_miss.append(item)
        for item in nums:
            if norm(item) not in stored_blob:
                n_miss.append(item)
        n_q = len(quoted)
        n_n = len(nums)
        per_q.append({
            "q_id": q["question_id"][:8], "stored": g1r["memories"],
            "quoted_total": n_q, "quoted_missing": q_miss,
            "quoted_recall": round(1 - len(q_miss) / n_q, 3) if n_q else None,
            "nums_total": n_n, "nums_missing_count": len(n_miss),
            "nums_recall": round(1 - len(n_miss) / n_n, 3) if n_n else None,
        })

    withq = [r for r in per_q if r["quoted_total"] > 0]
    withn = [r for r in per_q if r["nums_total"] > 0]
    q_mean = sum(r["quoted_recall"] for r in withq) / max(1, len(withq))
    n_mean = sum(r["nums_recall"] for r in withn) / max(1, len(withn))
    q_items_total = sum(r["quoted_total"] for r in withq)
    q_items_missing = sum(len(r["quoted_missing"]) for r in withq)
    print(f"questions with quoted items: {len(withq)}/156 | quoted-recall mean {q_mean:.3f} "
          f"| item-level: {q_items_total - q_items_missing}/{q_items_total}")
    print(f"questions with numbers: {len(withn)}/156 | nums-recall mean {n_mean:.3f}")
    worst = sorted(withq, key=lambda r: (r["quoted_recall"], -r["quoted_total"]))[:10]
    print("worst-10 quoted-recall:")
    for r in worst:
        print(f"  {r['q_id']} recall={r['quoted_recall']} ({r['quoted_total']-len(r['quoted_missing'])}/{r['quoted_total']}) "
              f"stored={r['stored']} missing={r['quoted_missing'][:4]}")

    out = {
        "provenance": {
            "label": "posthoc-exploratory diagnostic, NOT a prereg'd guard",
            "purpose": "verbatim-preservation measurement (B6-class visibility); R@5 saturated at 1.000",
            "source": "g1 stores (/tmp/opencode/mem0single156g1_*), dataset sessions",
            "extraction": "straight+curly quoted spans (3-80 chars, noise-guarded) + numeric tokens",
            "date": "2026-10-24",
        },
        "aggregate": {
            "questions_with_quoted": len(withq),
            "quoted_recall_mean": round(q_mean, 3),
            "quoted_items_total": q_items_total,
            "quoted_items_missing": q_items_missing,
            "nums_recall_mean": round(n_mean, 3),
        },
        "per_question": per_q,
    }
    (OUT / "verbatim_g1_v0.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("artifact: evals/results/verbatim_g1_v0.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
