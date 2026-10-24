#!/usr/bin/env python3
"""(verbatim v1.1) Council-corrected calibration metric (Обсуждение_23), posthoc.

Fixes vs v1 (all council-mandated BEFORE any threshold):
  1. Matching PRIMARY = case-insensitive + punctuation-normalized (council review point 3:
     v1 measured letter-case, not name preservation); exact-case recall reported apart.
  2. Aggregation PRIMARY = MICRO (item-weighted; council review point 1: v1's 0.241 was macro,
     775/4980=0.156 micro); macro reported as artifact line.
  3. Entity dedup across classes (council: titles+quoted double-registration counts once).
  4. Composition-failure exclusion (council review point 2 / council: stored<5 -> not a verbatim
     question; reported separately).
  5. Regex fixes (council: fix the cause): hyphenated TitleCase ("All-Purpose Flour"),
     trailing punctuation/whitespace strips; UI/structure blocklist.
  6. nums: raw verbatim recall AND digits-survive check (council review point 6: "70%" ~ "70 percent"
     arithmetic vs defect).
  7. Outputs the fixed PAIR PANEL proposal (council review point 7: (ii) primary = paired comparison
     on frozen panel, not global) + RANDOM-20 sample (council review point 4: worst-only bias check).
Posthoc-exploratory; NOT a guard; threshold fixed only in the (ii) prereg AFTER council.
"""
import glob
import json
import random
import re
from pathlib import Path

from qdrant_client import QdrantClient

DATA = Path(__file__).resolve().parent / "datasets/longmemeval/longmemeval_oracle.json"
G1_RES = Path("/home/aleksandr/Projects/MAQS_Way/evals/results/pilot_evidence_single156_g1.json")
OUT = Path(__file__).resolve().parent / "results"

DQ = re.compile(r'"([^"\n]{3,80})"')
CQ = re.compile(r"\u201c([^\u201d\n]{3,80})\u201d")
TITLE = re.compile(r"\b(?:[A-Z][\w-]*\s+){1,5}[A-Z][\w-]*\b")  # hyphen-aware, 2-6 words
PCT = re.compile(r"\d+(?:\.\d+)?\s?%")
CUR = re.compile(r"[$€£]\s?\d[\d,.]*")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")
DIGITS = re.compile(r"\d+(?:\.\d+)?")

STOP_SUBSTR = ("http", "www.", "@")
UI_BLOCKLIST = {
    "summary", "share", "tickets", "story", "freeze", "hanger", "provenance",
    "notable events", "purchase price", "dome date", "graduated", "pursued",
    "currently reading", "style inspiration", "fashion diary",
    "speaking of relationships", "acquisition date", "notes",
}


def clean_span(s):
    return s.strip().strip(",.;:!?")


def source_items(text):
    quoted = {clean_span(m.group(1)) for rx in (DQ, CQ) for m in rx.finditer(text)}
    titles = {clean_span(m.group(0)) for m in TITLE.finditer(text)}
    nums = {m.group(0) for rx in (PCT, CUR, YEAR) for m in rx.finditer(text)}
    out = {}
    for cls, items in (("quoted", quoted), ("titles", titles), ("nums", nums)):
        out[cls] = {i for i in items
                    if not any(s in i.lower() for s in STOP_SUBSTR)
                    and not any(i.lower() == b or i.lower().rstrip(",.") == b
                                for b in UI_BLOCKLIST)}
    return out["quoted"], out["titles"], out["nums"]


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s%$.]", " ", s).strip().lower())


def norm_exact(s):
    return re.sub(r"\s+", " ", s.strip()).lower()


def digits_of(s):
    return set(DIGITS.findall(s))


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
        raw = " ".join(r.payload.get("data", "") for r in pts)
        blob_norm = norm(raw)
        blob_exact = norm_exact(raw)
        blob_digits = set(DIGITS.findall(raw))

        entities = {norm(e) for e in (quoted | titles)}  # dedup across classes
        ent_exact = {norm_exact(e) for e in (quoted | titles)}
        ent_missing = [e for e in (quoted | titles) if norm(e) not in blob_norm]
        ent_missing_exact = [e for e in (quoted | titles)
                             if norm_exact(e) not in blob_exact]
        nums_raw_missing = [n for n in nums if norm(n) not in blob_norm]
        nums_digits_missing = [n for n in nums if not (digits_of(n) & blob_digits)]

        n_ent = len(quoted | titles)
        per_q.append({
            "q_id": q["question_id"][:8], "stored": g1r["memories"],
            "n_entities": n_ent,
            "n_missing_norm": len(ent_missing),
            "n_missing_exact": len(ent_missing_exact),
            "entity_recall_norm": round(1 - len(ent_missing) / n_ent, 3) if n_ent else None,
            "entity_recall_exact": round(1 - len(ent_missing_exact) / n_ent, 3) if n_ent else None,
            "n_nums": len(nums),
            "nums_recall_raw": round(1 - len(nums_raw_missing) / len(nums), 3) if nums else None,
            "nums_recall_digits": round(1 - len(nums_digits_missing) / len(nums), 3) if nums else None,
            "missing_entities": sorted(ent_missing)[:10],
            "nums_missing_raw": sorted(nums_raw_missing)[:6],
        })

    comp_fail = [r for r in per_q if r["stored"] < 5]
    panel = [r for r in per_q if r["n_entities"] > 0 and r["stored"] >= 5]

    def micro(rs, k):
        tot = sum(r["n_entities"] for r in rs)
        miss = sum(r["n_missing_norm"] for r in rs)
        return round((tot - miss) / max(1, tot), 3), tot

    def macro(rs, k):
        vals = [r[k] for r in rs if r[k] is not None]
        return round(sum(vals) / max(1, len(vals)), 3)

    micro_norm, tot_ent = micro(panel, None)
    micro_exact, _ = micro_panel_exact = (None, None)
    tot_exact_miss = sum(r["n_missing_exact"] for r in panel)
    micro_exact = round((tot_ent - tot_exact_miss) / max(1, tot_ent), 3)
    nums_raw = macro([r for r in panel if r["n_nums"] > 0], "nums_recall_raw")
    nums_digits = macro([r for r in panel if r["n_nums"] > 0], "nums_recall_digits")

    print(f"panel: {len(panel)} questions (entities>0, stored>=5); "
          f"composition-failures excluded: {len(comp_fail)} "
          f"({[r['q_id'] for r in comp_fail]})")
    print(f"PRIMARY (micro, item-weighted, case-insensitive+punct-norm): {micro_norm} "
          f"({tot_ent - sum(r['n_missing_norm'] for r in panel)}/{tot_ent})")
    print(f"exact-case micro: {micro_exact}")
    print(f"macro (per-question mean, norm): {macro(panel, 'entity_recall_norm')}")
    print(f"nums: raw {nums_raw} | digits-survive {nums_digits}")

    worst = sorted(panel, key=lambda r: (r["entity_recall_norm"], -r["n_entities"]))[:20]
    print("\nworst-20 (COMPLETE, panel):")
    for i, r in enumerate(worst, 1):
        print(f" {i:2d}. {r['q_id']} recall={r['entity_recall_norm']} "
              f"({r['n_entities']-r['n_missing_norm']}/{r['n_entities']}) stored={r['stored']} "
              f"| missing: {r['missing_entities'][:4]}")

    # fixed pair-panel proposal: top-12 by n_entities among panel
    top12 = sorted(panel, key=lambda r: -r["n_entities"])[:12]
    print("\nPAIR-PANEL proposal (top-12 by n_entities, frozen for (ii) prereg):")
    for r in top12:
        print(f"  {r['q_id']} n_entities={r['n_entities']} recall={r['entity_recall_norm']} stored={r['stored']}")

    # random-20 sample (seeded) for noise-share calibration
    rng = random.Random(42)
    rand20 = rng.sample([r for r in per_q if r["n_entities"] > 0], 20)
    print("\nRANDOM-20 (seed 42; noise-share calibration sample):")
    for r in rand20:
        print(f"  {r['q_id']} recall={r['entity_recall_norm']} "
              f"({r['n_entities']-r['n_missing_norm']}/{r['n_entities']}) stored={r['stored']} "
              f"| missing: {r['missing_entities'][:3]}")

    out = {
        "provenance": {
            "label": "posthoc-exploratory calibration v1.1 (council Обсуждение_23 fixes)",
            "fixes": "case-insensitive+punct-norm primary; micro aggregation primary; "
                     "entity dedup across classes; composition-failures (stored<5) excluded "
                     "and reported separately; hyphen-aware TitleCase; UI blocklist; "
                     "nums raw + digits-survive; pair-panel proposal; random-20 sample (seed 42)",
            "b2_column": "IMPOSSIBLE without b2 re-run (b2 artifact has no texts; stores wiped) "
                         "-- corrected twice in council record",
            "date": "2026-10-24",
        },
        "aggregate": {
            "panel_questions": len(panel),
            "composition_failures": [r["q_id"] for r in comp_fail],
            "primary_micro_recall_norm": micro_norm,
            "micro_recall_exact_case": micro_exact,
            "macro_recall_norm": macro(panel, "entity_recall_norm"),
            "nums_recall_raw": nums_raw,
            "nums_recall_digits_survive": nums_digits,
            "entities_total_in_panel": tot_ent,
        },
        "pair_panel_proposal": [r["q_id"] for r in top12],
        "random20_sample": [r["q_id"] for r in rand20],
        "per_question": per_q,
    }
    (OUT / "verbatim_g1_v11.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("\nartifact: evals/results/verbatim_g1_v11.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
