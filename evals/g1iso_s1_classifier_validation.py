#!/usr/bin/env python3
"""Out-of-sample validation of the tail/FP topic classifier (prereg-g1-iso
amend-2 sec 2, owner's signing condition).

The classifier was BUILT on g1-iso-b's 23 hits; here it is validated on data
it never saw: frozen g1 and g1-iso-a (KNOWN contamination -> the tail-class
share must land at the pre-set bands around 14.7%/14.9%), the known example
pairs (frozen g1 06f04340<-54026fce 'virtual coffee breaks'; g1-iso-a
195a1a1b<-32260d93) must classify as tail, and the physically tail-free
controls (g1-iso-a q0, g1-iso-b whole store, both part-B passes) must show
tail = 0. Pre-set tolerances are hardcoded from prereg-g1-iso-amend-2.md sec 2
(written BEFORE this validation ran). Fail -> amend-2 is not applied.
"""
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
DATA = HERE / "datasets/longmemeval/longmemeval_oracle.json"

WORD = re.compile(r"[a-z0-9]+")
STOP = set("user is the a an and or of to in on for with was were be been i my "
           "me you your it that this".split())
COVERAGE_FP = 0.6

# pre-set tolerances (amend-2 sec 2, ex ante)
BANDS = {
    "frozen_g1": {"raw": 274, "facts": 1680, "tail_min": 220, "tail_max": 275,
                  "fp_share_max": 0.025},
    "g1_iso_a": {"raw": 278, "facts": 1684, "tail_min": 220, "tail_max": 280,
                 "fp_share_max": 0.025},
}
KNOWN = [("frozen_g1", "06f04340", "54026fce"),
         ("g1_iso_a", "195a1a1b", "32260d93")]


def own_words(by, qid):
    q = by[qid]
    ws = set()
    for s in q["haystack_sessions"]:
        for m in s:
            ws.update(w for w in WORD.findall(str(m.get("content", "")).lower())
                      if w not in STOP and len(w) > 3)
    return ws


def classify_hit(by, hit):
    fw = [w for w in WORD.findall(hit["text"].lower())
          if w not in STOP and len(w) > 3]
    own = own_words(by, hit["q"])
    cover = sum(1 for w in fw if w in own) / max(1, len(fw))
    return ("FP" if cover >= COVERAGE_FP else "TAIL"), round(cover, 3)


def load_hits(path, getter):
    d = json.loads((OUT / path).read_text())
    return getter(d)


def main():
    data = json.loads(DATA.read_text())
    by = {}
    for q in data:
        by[q["question_id"]] = q
        by[q["question_id"].split("_")[-1]] = q

    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant",
                "single-session-preference")]
    pos = {q["question_id"]: i for i, q in enumerate(singles)}

    # gather confirmed hits per run
    runs = {}
    forensics = json.loads((OUT / "history_confound_forensics.json").read_text())
    runs["frozen_g1"] = [
        {"q": q, "foreign_q": x["foreign_q"], "text": x["text"]}
        for q, st in forensics["part_1b"]["g1"]["store"].items()
        for x in st["confirmed"]]
    a = json.loads((OUT / "g1iso_a_store_shingle_check.json").read_text())
    runs["g1_iso_a"] = [
        {"q": q, "foreign_q": x["foreign_q"], "text": x["text"]}
        for q, h in a["hits"].items() for x in h["confirmed"]]
    b = json.loads((OUT / "g1iso_store_shingle_check_b.json").read_text())
    runs["g1_iso_b"] = [
        {"q": q, "foreign_q": x["foreign_q"], "text": x["text"]}
        for q, h in b["passes"]["single156"]["hits"].items()
        for x in h["confirmed"]]
    p = json.loads((OUT / "g1iso_store_shingle_check_panel.json").read_text())
    for pname in ("pass0", "pass1"):
        runs[f"panel_{pname}"] = [
            {"q": q, "foreign_q": x["foreign_q"], "text": x["text"]}
            for q, h in p["passes"][pname]["hits"].items()
            for x in h["confirmed"]]

    report, verdicts = {}, []
    for name, hits in runs.items():
        cls = {}
        for h in hits:
            c, cov = classify_hit(by, h)
            cls.setdefault(c, []).append({**h, "class": c, "coverage": cov})
        report[name] = {
            "raw_confirmed": len(hits),
            "tail": len(cls.get("TAIL", [])),
            "fp": len(cls.get("FP", [])),
            "tail_hits": cls.get("TAIL", [])[:12],
        }
        print(f"{name}: raw={len(hits)} tail={report[name]['tail']} "
              f"fp={report[name]['fp']}")

    # criterion 1: known-contamination runs land in the pre-set bands
    for name in ("frozen_g1", "g1_iso_a"):
        band = BANDS[name]
        r = report[name]
        fp_share = r["fp"] / band["facts"]
        ok_band = band["tail_min"] <= r["tail"] <= band["tail_max"]
        ok_fp = fp_share <= band["fp_share_max"]
        verdicts.append((f"{name}: tail {r['tail']} in "
                         f"[{band['tail_min']},{band['tail_max']}]", ok_band))
        verdicts.append((f"{name}: FP share {fp_share*100:.2f}% <= "
                         f"{band['fp_share_max']*100:.1f}%", ok_fp))

    # criterion 2: known examples classify as TAIL
    for run_name, qid, fqid in KNOWN:
        qfull = qid if qid in by and qid in pos else "gpt4_" + qid
        ffull = fqid if fqid in by and "gpt4_" + fqid not in pos else "gpt4_" + fqid
        hits = [h for h in runs[run_name]
                if h["q"].split("_")[-1] == qid and h["foreign_q"].split("_")[-1] == fqid]
        n_tail = sum(1 for h in hits
                     if classify_hit(by, h)[0] == "TAIL")
        pq, pf = pos.get("gpt4_" + qid, pos.get(qid)), pos.get("gpt4_" + fqid, pos.get(fqid))
        verdicts.append((f"known example {run_name} {qid}<-{fqid} "
                         f"(pos {pq}<-{pf}): {n_tail}/{len(hits)} tail", n_tail == len(hits) and len(hits) > 0))

    # criterion 3: tail-free controls -> tail = 0
    # (g1_iso_a as a RUN is known-contaminated and checked by its band above;
    # its tail-free control is question 0 only, checked right after)
    for ctrl in ("g1_iso_b", "panel_pass0", "panel_pass1"):
        verdicts.append((f"control {ctrl}: tail = 0", report[ctrl]["tail"] == 0))
    # g1-iso-a q0 specifically (physically empty tail)
    q0 = singles[0]["question_id"]
    a_q0 = [h for h in runs["g1_iso_a"] if h["q"] == q0]
    tail_q0 = sum(1 for h in a_q0 if classify_hit(by, h)[0] == "TAIL")
    verdicts.append((f"control g1_iso_a q0 ({q0[:12]}): tail = 0", tail_q0 == 0))
    # frozen g1 q0: physical cross-run tail from b4 -- observation, no criterion
    fg_q0 = [h for h in runs["frozen_g1"] if h["q"] == q0]
    obs_tail_q0 = sum(1 for h in fg_q0 if classify_hit(by, h)[0] == "TAIL")
    print(f"observation frozen_g1 q0: {len(fg_q0)} hits, tail-class {obs_tail_q0} "
          f"(its physical tail was b4's last session, cross-run)")

    all_ok = all(ok for _, ok in verdicts)
    out = {
        "provenance": {
            "date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "rule": "amend-2 sec 2, pre-set tolerances (ex ante)",
            "classifier": "own-haystack topic coverage of fact words "
                          f"(>3 chars, no stopwords); FP if >= {COVERAGE_FP}",
            "posthoc_marker": "amend-2 is POSTHOC per owner; this validation "
                              "is the signing condition",
        },
        "runs": report,
        "verdicts": [{"check": c, "ok": ok} for c, ok in verdicts],
        "observation_frozen_g1_q0": {"hits": len(fg_q0), "tail": obs_tail_q0},
        "all_passed": all_ok,
    }
    (OUT / "g1iso_classifier_validation.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    for c, ok in verdicts:
        print(f"  [{'OK' if ok else 'FAIL'}] {c}")
    print(f"VALIDATION: {'PASSED — amend-2 applies' if all_ok else 'FAILED — amend-2 NOT applied'}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    sys.exit(main())
