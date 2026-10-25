#!/usr/bin/env python3
"""g1-iso verbatim v1.2 on the frozen 12-question pair panel (prereg-g1-iso.md
sec 3.3, owner correction 2).

Computes the (ii)-line metric (verbatim v1.2: N1-N8 noise classes FROZEN) on the
g1-iso stores, using the frozen classifier by import from verbatim_v12.py (no
edits to the frozen tool), and compares the panel-mean against the frozen g1
base 0.162. Pre-set threshold: |panel_mean_iso - 0.162| > 0.03 -> the (ii)
verdict gets annotated 'measured under confound, re-run pending' and the
(ii)-iso package goes to the owner (the (ii) verdict itself is NEVER
rewritten). Within threshold -> annotation 'baseline within tolerance'.

Exit 0 either way (this is a verdict, not a gate); the artifact carries it.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verbatim_v12 as v12  # frozen classifier: classify_noise, norm, source_items

from qdrant_client import QdrantClient

HERE = Path(__file__).resolve().parent
DATA = HERE / "datasets/longmemeval/longmemeval_oracle.json"
OUT = HERE / "results"
FROZEN_V12 = OUT / "verbatim_g1_v12.json"
PANEL_BASE_MEAN = 0.162      # frozen in prereg-ii.md sec 1
SHIFT_THRESHOLD = 0.03       # pre-set in prereg-g1-iso.md sec 3.3


def main():
    import glob
    cands = sorted(glob.glob("/tmp/opencode/mem0single156g1iso_*"))
    if not cands:
        print("no g1-iso store found")
        return 2
    store_root = cands[-1]
    print(f"store: {store_root}")

    frozen = json.loads(FROZEN_V12.read_text())
    panel_ids = frozen["pair_panel_stratified"]  # frozen 12 full ids
    frozen_by_q = {r["q_id"]: r for r in frozen["per_question"]}
    assert len(panel_ids) == 12, panel_ids

    data = json.loads(DATA.read_text())
    singles = [q for q in data if q["question_type"] in
               ("single-session-user", "single-session-assistant",
                "single-session-preference")]
    assert len(singles) == 156

    per_q = []
    for qi, q in enumerate(singles):
        qid = q["question_id"]
        sess_text = "\n".join(str(m.get("content", "")) for m in q["haystack_sessions"][0])
        items, nums = v12.source_items(sess_text)
        client = QdrantClient(path=f"{store_root}/q{qi}")
        pts, _ = client.scroll(collection_name=f"s156g1_{qi}", limit=100,
                               with_payload=True, with_vectors=False)
        client.close()
        blob = v12.norm(" ".join(r.payload.get("data", "") for r in pts))
        kept = missed = 0
        miss_signal = []
        for it in items:
            nc = v12.classify_noise(it)
            if nc:
                continue
            if v12.norm(it) in blob:
                kept += 1
            else:
                missed += 1
                miss_signal.append(it)
        n_sig = kept + missed
        per_q.append({"q_id": qid,
                      "n_signal": n_sig,
                      "stored": len(pts),
                      "recall_clean": round(kept / n_sig, 3) if n_sig else None,
                      "missing_preview": miss_signal[:6]})
    by_q = {r["q_id"]: r for r in per_q}

    members = []
    for qid in panel_ids:
        iso = by_q[qid]
        base = frozen_by_q[qid]
        members.append({
            "q_id": qid,
            "n_signal_frozen": base["n_signal"], "n_signal_iso": iso["n_signal"],
            "recall_frozen": base["recall_clean"], "recall_iso": iso["recall_clean"],
            "stored_frozen": base["stored"], "stored_iso": iso["stored"],
        })
    iso_vals = [m["recall_iso"] for m in members if m["recall_iso"] is not None]
    panel_mean_iso = round(sum(iso_vals) / len(iso_vals), 4)
    delta = round(abs(panel_mean_iso - PANEL_BASE_MEAN), 4)
    exceeded = delta > SHIFT_THRESHOLD
    verdict = (f"SHIFT {delta} > {SHIFT_THRESHOLD}: annotate the (ii) verdict "
               "'measured under confound, re-run pending'; (ii)-iso package to owner"
               if exceeded else
               f"WITHIN TOLERANCE (|delta| = {delta} <= {SHIFT_THRESHOLD}): annotate "
               "'baseline within tolerance'; full-500 not re-run")

    micro_vals = [r for r in (by_q[q]["recall_clean"] for q in
                 [m["q_id"] for m in members]) if r is not None]

    out = {
        "provenance": {
            "date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "store": store_root,
            "metric": "verbatim v1.2 (frozen N1-N8 classes, import from verbatim_v12.py)",
            "panel": "frozen pair_panel_stratified from verbatim_g1_v12.json (12 ids)",
            "panel_base_mean": PANEL_BASE_MEAN,
            "shift_threshold": SHIFT_THRESHOLD,
        },
        "panel_mean_iso": panel_mean_iso,
        "panel_mean_frozen": PANEL_BASE_MEAN,
        "abs_delta": delta,
        "threshold_exceeded": exceeded,
        "verdict": verdict,
        "members": members,
        "global_micro_reference": round(sum(micro_vals) / len(micro_vals), 3),
    }
    (OUT / "g1iso_verbatim_v12_panel.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"panel-mean iso = {panel_mean_iso} vs frozen base {PANEL_BASE_MEAN} "
          f"| delta = {delta} (threshold {SHIFT_THRESHOLD})")
    for m in members:
        print(f"  {m['q_id'][:16]:16s} n={m['n_signal_iso']:4d} "
              f"iso={m['recall_iso']} frozen={m['recall_frozen']} "
              f"stored {m['stored_frozen']}->{m['stored_iso']}")
    print(f"VERDICT: {verdict}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
