#!/usr/bin/env python3
"""g1-iso primary fix check (prereg-g1-iso.md sec 1, owner correction 1).

Runs the SAME unique-shingle foreign-fact detector that measured the leaks in
the frozen g1 stores (16.3% confirmed) against the g1-iso stores. Expected 0:
g1-iso extraction prompts carry no history tail, so any confirmed hit is a
detector FALSE POSITIVE -- the negative control that calibrates the frozen
estimate (corrected g1 rate = 16.31% - measured FP rate).

Tolerance (pre-set in the prereg from manual hit verification on frozen g1,
where 5/5 checked hits were genuine): confirmed <= 5 facts (<=0.35%) in <= 5
questions, weak <= 20. In tolerance -> exit 0 (fix confirmed, detector
calibrated); out -> exit 1 (STOP, finding to owner before any other verdict).

Read-only on the live stores (copies); reuses the frozen detector mechanics by
import from history_confound_forensics.py (no classifier edits).
"""
import json
import shutil
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from history_confound_forensics import load_dataset, scan_texts, shingle_map

from qdrant_client import QdrantClient

HERE = Path(__file__).resolve().parent
OUT = HERE / "results"
WORK = Path("/tmp/opencode/forensics_work_g1iso")
TOL_CONFIRMED_FACTS = 5
TOL_CONFIRMED_QUESTIONS = 5
TOL_WEAK = 20
FROZEN_G1_RATE = 274 / 1680  # 16.31%, history_confound_forensics.json




PANEL8 = ["75832dbd", "0a34ad58", "1faac195", "b0479f84",
          "fca70973", "311778f1", "afdc33df", "19b5f2b3",
          "e47becba", "58bf7951", "3b6f954b", "faba32e5"]


def read_dir_texts(src):
    """Read all collections of one qdrant dir (copy first). Returns texts."""
    dst = WORK / src.name
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst)
    cli = QdrantClient(path=str(dst))
    texts = []
    for coll in [c.name for c in cli.get_collections().collections]:
        off = None
        while True:
            pts, off = cli.scroll(collection_name=coll, limit=512,
                                  offset=off, with_payload=True)
            for p in pts:
                t = (p.payload or {}).get("data") or (p.payload or {}).get("text") or ""
                if t:
                    texts.append(t)
            if off is None:
                break
    cli.close()
    return texts


def main():
    t0 = time.time()
    if len(sys.argv) > 1:
        store_root = sys.argv[1]
    else:
        import glob
        cands = sorted(glob.glob("/tmp/opencode/mem0single156g1iso_b_*") or
                       glob.glob("/tmp/opencode/g1iso_panel12_*"))
        if not cands:
            print("no store found; pass the store root as argv[1]")
            return 2
        store_root = cands[-1]
    print(f"store: {store_root}")

    data, singles, _ = load_dataset()
    print(f"[1] shingle index... ({time.time() - t0:.0f}s)")
    uniq = shingle_map(data)
    print(f"    unique shingles: {len(uniq)} ({time.time() - t0:.0f}s)")

    root = Path(store_root)
    passes = {}
    if (root / "pass0").is_dir():  # panel-12 layout (prereg part B): per-pass check
        by8 = {q["question_id"].split("_")[-1]: q for q in data}
        panel = [by8[h] for h in PANEL8]
        for pi in (0, 1):
            per_q = {}
            for qi, q in enumerate(panel):
                src = root / f"pass{pi}" / f"q{qi}"
                per_q[q["question_id"]] = read_dir_texts(src) if src.is_dir() else None
            passes[f"pass{pi}"] = per_q
    else:  # single-156 layout
        per_q = {}
        for qi, q in enumerate(singles):
            src = root / f"q{qi}"
            per_q[q["question_id"]] = read_dir_texts(src) if src.is_dir() else None
        passes["single156"] = per_q
    # fail-closed: a store with no readable question dirs is a bad invocation,
    # never a vacuous pass
    n_readable = sum(1 for p in passes.values()
                     for t in p.values() if t is not None and t)
    if n_readable == 0:
        print(f"no readable question stores under {store_root} -- fail-closed")
        return 2

    results, worst = {}, True
    for pname, per_q in passes.items():
        scan = scan_texts({q: t for q, t in per_q.items() if t is not None}, uniq)
        conf_facts = sum(len(s["confirmed"]) for s in scan.values())
        weak_facts = sum(len(s["weak"]) for s in scan.values())
        conf_qs = sum(1 for s in scan.values() if s["confirmed"])
        n_facts = sum(s["n_facts"] for s in scan.values())
        fp_rate = conf_facts / max(1, n_facts)
        in_tol = (conf_facts <= TOL_CONFIRMED_FACTS and
                  conf_qs <= TOL_CONFIRMED_QUESTIONS and weak_facts <= TOL_WEAK)
        worst = worst and in_tol
        results[pname] = {
            "n_facts": n_facts, "confirmed_facts": conf_facts,
            "confirmed_questions": conf_qs, "weak_facts": weak_facts,
            "detector_fp_rate": round(fp_rate, 5), "in_tolerance": in_tol,
            "hits": {q: {"confirmed": s["confirmed"], "weak": s["weak"]}
                     for q, s in scan.items() if s["confirmed"] or s["weak"]},
        }
        print(f"[{pname}] confirmed={conf_facts} in {conf_qs} q; "
              f"weak={weak_facts}; facts={n_facts}; in_tol={in_tol}")

    corrected_frozen = max(0.0, FROZEN_G1_RATE - max(
        r["detector_fp_rate"] for r in results.values()))
    verdict = ("FIX CONFIRMED — foreign facts within detector noise in every "
               f"checked pass; frozen-g1 estimate corrected to "
               f"{corrected_frozen * 100:.1f}% (raw 16.31%)"
               if worst else
               "OUT OF TOLERANCE — STOP: hits exceed the pre-set detector-FP "
               "budget; finding to owner before any other verdict")

    out = {
        "provenance": {
            "date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "store": store_root,
            "detector": "identical to history_confound_forensics (unique 5-word "
                        "shingles; confirmed >=2, weak ==1)",
            "tolerance": {"confirmed_facts": TOL_CONFIRMED_FACTS,
                          "confirmed_questions": TOL_CONFIRMED_QUESTIONS,
                          "weak": TOL_WEAK},
            "frozen_g1_reference": {"confirmed": 274, "facts": 1680,
                                    "rate": round(FROZEN_G1_RATE, 4)},
        },
        "passes": results,
        "corrected_frozen_g1_rate": round(corrected_frozen, 4),
        "in_tolerance": worst,
        "verdict": verdict,
    }
    suffix = "_panel" if (root / "pass0").is_dir() else "_b"
    (OUT / f"g1iso_store_shingle_check{suffix}.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"corrected frozen-g1 estimate: {corrected_frozen * 100:.1f}% (raw 16.31%)")
    print(f"VERDICT: {verdict}")
    return 0 if worst else 1


if __name__ == "__main__":
    sys.exit(main())
