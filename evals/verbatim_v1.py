#!/usr/bin/env python3
"""(verbatim v1) Posthoc-exploratory, council-designed (Обсуждение_22, Q4):
v0 measured quoted spans only (baseline 0.187). v1 widens per the B6 defect definition
("название/имя теряется в перефразе"): title-case sequences + quoted spans +
contextual numbers (percent / currency / year). Per-class recall reported separately;
combined-signal recall = candidate baseline for the (ii) primary guard (threshold to be
fixed in the (ii) prereg AFTER worst-20 manual calibration, BEFORE the run).
Runs on live g1 stores; NOT a prereg'd guard; label: posthoc-exploratory.
"""
import glob
import json
import re
from pathlib import Path

from qdrant_client import QdrantClient

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
G1_RES = Path(__file__).resolve().parent / "results/pilot_evidence_single156_g1.json"
OUT = Path(__file__).resolve().parent / "results"

DQ = re.compile(r'"([^"\n]{3,80})"')
CQ = re.compile(r"\u201c([^\u201d\n]{3,80})\u201d")
TITLE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,5}\b")   # 2-6 TitleCase words
PCT = re.compile(r"\d+(?:\.\d+)?\s?%")
CUR = re.compile(r"[$€£]\s?\d[\d,.]*")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

STOP_SUBSTR = ("http", "www.", "@", "u2019")  # noise guards


def source_items(text):
    quoted = {m.group(1).strip() for rx in (DQ, CQ) for m in rx.finditer(text)}
    quoted = {q for q in quoted if not any(s in q.lower() for s in STOP_SUBSTR)}
    titles = {m.group(0) for m in TITLE.finditer(text)}
    titles = {t for t in titles if not any(s in t.lower() for s in STOP_SUBSTR)}
    nums = {m.group(0) for rx in (PCT, CUR, YEAR) for m in rx.finditer(text)}
    return quoted, titles, nums


def norm(s):
    return re.sub(r"\s+", " ", s.strip().lower())


def main():
    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant", "single-session-preference")]
    g1 = json.loads(G1_RES.read_text())["results"]
    assert len(singles) == len(g1) == 156

    store_root = sorted(glob.glob("/tmp/opencode/mem0single156g1_*"))[-1]

    per_q = []
    for qi, (q, g1r) in enumerate(zip(singles, g1)):
        sess_text = "\n".join(str(m.get("content", "")) for m in q["haystack_sessions"][0])
        quoted, titles, nums = source_items(sess_text)
        client = QdrantClient(path=f"{store_root}/q{qi}")
        pts, _ = client.scroll(collection_name=f"s156g1_{qi}", limit=100,
                               with_payload=True, with_vectors=False)
        client.close()
        blob = norm(" ".join(r.payload.get("data", "") for r in pts))
        rec = {}
        miss = {}
        for cls, items in (("quoted", quoted), ("titles", titles), ("nums", nums)):
            m_ = [i for i in items if norm(i) not in blob]
            miss[cls] = m_
            rec[cls] = round(1 - len(m_) / len(items), 3) if items else None
        signal = quoted | titles | nums
        sm = [i for i in signal if norm(i) not in blob]
        per_q.append({
            "q_id": q["question_id"][:8], "stored": g1r["memories"],
            "n_signal": len(signal), "signal_missing_count": len(sm),
            "recall_quoted": rec["quoted"], "recall_titles": rec["titles"],
            "recall_nums": rec["nums"],
            "recall_signal": round(1 - len(sm) / len(signal), 3) if signal else None,
            "missing": {"quoted": miss["quoted"][:6], "titles": miss["titles"][:8],
                        "nums": miss["nums"][:6]},
        })

    withsig = [r for r in per_q if r["n_signal"] > 0]
    agg = lambda k: round(sum(r[k] for r in withsig if r[k] is not None) /
                          max(1, sum(1 for r in withsig if r[k] is not None)), 3)
    sig_mean = sum(r["recall_signal"] for r in withsig) / max(1, len(withsig))
    items_total = sum(r["n_signal"] for r in withsig)
    items_missed = sum(r["signal_missing_count"] for r in withsig)
    print(f"questions with signal: {len(withsig)}/156")
    print(f"recall: quoted={agg('recall_quoted')} titles={agg('recall_titles')} "
          f"nums={agg('recall_nums')} SIGNAL={sig_mean:.3f}")
    print(f"item-level signal: {items_total - items_missed}/{items_total}")
    worst = sorted(withsig, key=lambda r: (r["recall_signal"], -r["n_signal"]))[:20]
    print("\nworst-20 (calibration material for council):")
    for r in worst:
        print(f"  {r['q_id']} recall={r['recall_signal']} ({r['n_signal']-r['signal_missing_count']}/{r['n_signal']}) "
              f"stored={r['stored']}")
        print(f"    titles_missing={r['missing']['titles'][:4]}")
        print(f"    quoted_missing={r['missing']['quoted'][:2]} nums_missing={r['missing']['nums'][:3]}")

    out = {
        "provenance": {
            "label": "posthoc-exploratory diagnostic, NOT a prereg'd guard",
            "design": "council Обсуждение_22 Q4: titles(TitleCase 2-6 words) UNION quoted UNION "
                      "contextual nums (percent/currency/year); per-class recall reported; "
                      "combined signal = candidate (ii) primary-guard baseline",
            "calibration": "worst-20 manual review REQUIRED before threshold fixed in prereg (ii)",
            "source": "g1 stores (/tmp/opencode/mem0single156g1_*), dataset sessions",
            "date": "2026-10-24",
        },
        "aggregate": {
            "questions_with_signal": len(withsig),
            "recall_signal_mean": round(sig_mean, 3),
            "recall_quoted_mean": agg("recall_quoted"),
            "recall_titles_mean": agg("recall_titles"),
            "recall_nums_mean": agg("recall_nums"),
            "signal_items_total": items_total,
            "signal_items_missed": items_missed,
        },
        "per_question": per_q,
    }
    (OUT / "verbatim_g1_v1.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("\nartifact: evals/results/verbatim_g1_v1.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
