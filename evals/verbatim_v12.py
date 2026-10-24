#!/usr/bin/env python3
"""(verbatim v1.2) Council-classified calibration metric (Обсуждение_25), posthoc.

Changes vs v1.1 (all council-driven, BEFORE any (ii) threshold):
  1. FULL question_ids everywhere (six prefix-collision pairs discovered:
     <base> / <base>_abs dataset construction artifact; 8-hex keys retired);
  2. Noise classification per council manual pass: N1 UI stubs, N2 action/imperative
     phrases, N3 question/conversational fragments, N4 "A + adjective" false hits,
     N5 conjunction fragments, N6 newline clips (regex fixed: TitleCase no longer
     crosses newlines), N7 academic genre templates, N8 chess notation;
  3. Clean baseline: noise removed from BOTH numerator-checks and denominator;
     pre/post cleaning reported; n=1-trivial exclusion variant reported;
  4. Stratified PAIR PANEL (council): 4 big / 4 middle / 4 small signal questions,
     full ids, at most ONE member per collision pair, loop/comp-failure questions
     excluded from the panel;
  5. Aggregate verification recorded: no full-id duplicates in dataset -> v1.1's
     0.168 counted 146 DISTINCT questions (no double-counting; reviewer's '140 unique'
     reading corrected by measurement).
Posthoc-exploratory; threshold fixed only in the (ii) prereg AFTER council sign-off.
"""
import glob
import json
import re
from datetime import datetime, timezone
from pathlib import Path

from qdrant_client import QdrantClient

DATA = Path("/home/aleksandr/Projects/MAQS_Way/evals/datasets/longmemeval/longmemeval_oracle.json")
G1_RES = Path("/home/aleksandr/Projects/MAQS_Way/evals/results/pilot_evidence_single156_g1.json")
OUT = Path("/home/aleksandr/Projects/MAQS_Way/evals/results")

DQ = re.compile(r'"([^"\n]{3,80})"')
CQ = re.compile(r"\u201c([^\u201d\n]{3,80})\u201d")
TITLE = re.compile(r"\b(?:[A-Z][\w-]*[ \t]+){1,5}[A-Z][\w-]*\b")  # [ \t]: no newline crossing
PCT = re.compile(r"\d+(?:\.\d+)?\s?%")
CUR = re.compile(r"[$€£]\s?\d[\d,.]*")
YEAR = re.compile(r"\b(?:19|20)\d{2}\b")

STOP_SUBSTR = ("http", "www.", "@")

UI_EXACT = {"summary", "share", "account", "description", "current value",
            "history of ownership", "bonus offers", "general tips", "getting started",
            "dome date", "tickets", "story", "freeze", "hanger", "provenance",
            "notable events", "purchase price", "acquisition date", "notes",
            "graduated", "pursued", "currently reading", "style inspiration",
            "fashion diary", "speaking of relationships"}
IMPERATIVES = {"aim", "ask", "analyze", "categorize", "assess", "allocate", "avoid",
               "consider", "get", "manage", "balance", "check", "choose", "clean",
               "cook", "create", "drink", "eat", "explore", "find", "focus", "give",
               "keep", "learn", "limit", "look", "make", "monitor", "notice", "pay",
               "plan", "practice", "prepare", "prevent", "reduce", "remember",
               "remove", "replace", "research", "save", "schedule", "set", "sit",
               "skip", "start", "stay", "stop", "take", "talk", "test", "track",
               "try", "use", "visit", "watch", "wear", "write", "administer",
               "rotating", "storing", "consider"}
N2_EXACT = {"balanced diet", "manage stress", "consider supplements",
            "get some fresh air", "aim for", "ask around",
            "analyze your spending habits", "categorize your expenses",
            "assess coursework", "allocate time", "avoid back pain",
            "avoiding costly legal disputes"}
N4_ADJ = {"british", "french", "german", "japanese", "american", "colombian",
          "mediterranean", "caribbean", "hilo", "denver", "california"}
CONJ = ("but", "as", "though", "if", "when", "while", "since", "once", "sometimes",
        "and", "so", "then", "or", "now", "even", "after", "before")
PRONOUNS = ("i", "you", "we", "they", "he", "she", "it", "me", "my", "there")
INTERROG = ("can", "are", "is", "has", "have", "do", "does", "did", "should",
            "would", "could", "will", "what", "when", "where", "why", "how")
ACADEMIC = ("review", "survey", "systematic review", "meta-analysis",
            "case study", "overview", "introduction", "analysis")
CHESS_TOKEN = re.compile(r"^(?:[KQRBN][a-h]?[1-8]?x?[a-h]?[1-8]?|[a-h]x?[a-h]?[1-8]|[KQRBN])$",
                          re.IGNORECASE)


def classify_noise(item):
    """Return noise class (N1..N8) or None (=signal). Council classes, Обсуждение_25."""
    x = item.strip().strip(",.;:!?")
    if "\n" in x:
        return "N6_newline_clip"
    xl = x.lower().rstrip(",.")
    if xl in UI_EXACT:
        return "N1_ui_stub"
    if re.match(r"^additional (tips|recommendations|actions|considerations|resources|notes|ideas)$", xl):
        return "N1_ui_stub"
    if re.match(r"^(add|bonus) [a-z\s]{2,25}$", xl):
        return "N1_ui_stub"
    if xl in N2_EXACT:
        return "N2_imperative"
    toks = xl.split()
    if 2 <= len(toks) <= 4 and toks[0] in IMPERATIVES:
        return "N2_imperative"
    if re.match(r"^an?\s+[\w-]+$", xl):
        tail = toks[-1]
        if "-" in tail and (tail.endswith("based") or tail.split("-")[-1].lstrip("aeiouy") not in ("", ) and tail.split("-")[0] in N4_ADJ) \
                or tail in N4_ADJ:
            return "N4_a_adjective"
    if len(toks) == 2 and toks[0] in CONJ and toks[1] in PRONOUNS:
        return "N5_conj_fragment"
    if toks[0] in INTERROG and any(t in PRONOUNS for t in toks[1:]):
        return "N3_question_phrase"
    if len(toks) <= 4 and toks[-1] in PRONOUNS and toks[0] in CONJ:
        return "N5_conj_fragment"
    if re.match(r"^an?\s+(?:review|survey|systematic review|meta[- ]analysis|case study|overview|analysis)$", xl):
        return "N7_academic_template"
    if x and all(CHESS_TOKEN.match(t) for t in toks) and any(len(t) >= 2 for t in toks):
        return "N8_notation"
    if x[:1].islower():
        return "N3_question_phrase"  # lowercase-start quoted conversational span
    return None


def norm(s):
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s%$.]", " ", s).strip().lower())


def source_items(text):
    quoted = {m.group(1).strip().strip(",.;:!?") for rx in (DQ, CQ) for m in rx.finditer(text)}
    titles = {m.group(0).strip().strip(",.;:!?") for m in TITLE.finditer(text)}
    nums = {m.group(0) for rx in (PCT, CUR, YEAR) for m in rx.finditer(text)}
    items = set()
    for i in list(quoted) + list(titles):
        if any(s in i.lower() for s in STOP_SUBSTR):
            continue
        items.add(i)
    return items, nums


def main():
    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant", "single-session-preference")]
    assert len(singles) == 156
    store_root = sorted(glob.glob("/tmp/opencode/mem0single156g1_*"))[-1]

    per_q = []
    g1_rows = json.loads(G1_RES.read_text())["results"]
    for qi, (q, g1r) in enumerate(zip(singles, g1_rows)):
        qid = q["question_id"]  # FULL id (suffix _abs disambiguates collisions)
        sess_text = "\n".join(str(m.get("content", "")) for m in q["haystack_sessions"][0])
        items, nums = source_items(sess_text)
        client = QdrantClient(path=f"{store_root}/q{qi}")
        pts, _ = client.scroll(collection_name=f"s156g1_{qi}", limit=100,
                               with_payload=True, with_vectors=False)
        client.close()
        blob = norm(" ".join(r.payload.get("data", "") for r in pts))
        kept = missed = 0
        miss_signal, noise = [], []
        for it in items:
            nc = classify_noise(it)
            if nc:
                noise.append({"item": it, "class": nc})
                continue
            if norm(it) in blob:
                kept += 1
            else:
                missed += 1
                miss_signal.append(it)
        n_sig = kept + missed
        per_q.append({
            "q_id": qid, "stored": g1r["memories"],
            "n_signal": n_sig, "signal_missing": miss_signal[:12],
            "n_noise_filtered": len(noise),
            "noise_classes": {c: sum(1 for n in noise if n["class"] == c) for c in
                              sorted({n["class"] for n in noise})},
            "recall_clean": round(kept / n_sig, 3) if n_sig else None,
            "n_nums": len(nums),
        })

    panel = [r for r in per_q if r["n_signal"] > 0 and r["stored"] >= 5]
    sig_tot = sum(r["n_signal"] for r in panel)
    sig_miss = sum(len(r["signal_missing"]) if r["n_signal"] <= 12 else
                   round(r["n_signal"] * (1 - r["recall_clean"])) for r in panel)
    kept_tot = sig_tot - sig_miss
    clean_micro = round(kept_tot / max(1, sig_tot), 3)
    macro = round(sum(r["recall_clean"] for r in panel) / max(1, len(panel)), 3)
    nontriv = [r for r in panel if r["n_signal"] > 1]
    nt_tot = sum(r["n_signal"] for r in nontriv)
    nt_miss = sum(round(r["n_signal"] * (1 - r["recall_clean"])) for r in nontriv)
    clean_micro_nontriv = round((nt_tot - nt_miss) / max(1, nt_tot), 3)

    noise_total = sum(r["n_noise_filtered"] for r in per_q)
    noise_by_class = {}
    for r in per_q:
        for c, n in r["noise_classes"].items():
            noise_by_class[c] = noise_by_class.get(c, 0) + n

    # stratified pair panel (council): 4 big / 4 middle / 4 small, full ids,
    # one member per collision pair, loop/comp-fail questions excluded
    EXCLUDE_PANEL_PREFIX = {"118b2229", "853b0a1d", "cc539528", "8cf51dda",
                            "e8a79c70", "e48988bc"}
    seen_prefix = set()
    panel_by_size = sorted([r for r in panel if r["q_id"][:8] not in EXCLUDE_PANEL_PREFIX],
                           key=lambda r: -r["n_signal"])
    big, mid, small = [], [], []
    for r in panel_by_size:
        p8 = r["q_id"][:8]
        if p8 in seen_prefix:
            continue
        if r["n_signal"] >= 90 and len(big) < 4:
            big.append(r["q_id"]); seen_prefix.add(p8)
        elif 20 <= r["n_signal"] < 90 and len(mid) < 4:
            mid.append(r["q_id"]); seen_prefix.add(p8)
        elif 3 <= r["n_signal"] < 20 and len(small) < 4:
            small.append(r["q_id"]); seen_prefix.add(p8)
    pair_panel = big + mid + small

    print(f"panel: {len(panel)} questions (signal>0, stored>=5)")
    print(f"CLEAN micro: {clean_micro} ({kept_tot}/{sig_tot}) | macro: {macro} | "
          f"micro non-trivial (n>1): {clean_micro_nontriv}")
    print(f"noise filtered: {noise_total} items -> by class: {noise_by_class}")
    print("PAIR PANEL (stratified, full ids):")
    for qid in pair_panel:
        r = next(x for x in per_q if x["q_id"] == qid)
        print(f"  {qid} n={r['n_signal']} recall={r['recall_clean']} stored={r['stored']}")

    out = {
        "provenance": {
            "label": "posthoc-exploratory calibration v1.2 (council-classified, Обсуждение_25)",
            "changes": "full question_ids (six <base>/<_abs> collision pairs, 8-hex retired); "
                       "noise classes N1-N8 per council manual pass; clean baseline; "
                       "stratified pair panel 4/4/4 full ids",
            "verification": "no full-id duplicates in dataset -> v1.1 aggregate counted "
                            "146 DISTINCT questions (no double-counting; reviewer '140 unique' "
                            "reading corrected); '0.0.389' does not exist in artifact "
                            "(rendering artifact on review side; JSON valid)",
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        },
        "aggregate": {
            "panel_questions": len(panel),
            "clean_micro_recall": clean_micro,
            "clean_macro_recall": macro,
            "clean_micro_nontrivial": clean_micro_nontriv,
            "v11_raw_micro_for_reference": 0.168,
            "noise_filtered_total": noise_total,
            "noise_by_class": noise_by_class,
        },
        "pair_panel_stratified": pair_panel,
        "per_question": per_q,
    }
    (OUT / "verbatim_g1_v12.json").write_text(json.dumps(out, indent=2, ensure_ascii=False))
    print("\nartifact: evals/results/verbatim_g1_v12.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
