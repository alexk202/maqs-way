#!/usr/bin/env python3
"""RTX-stand verification of the run_stand2_panel12.py canary harness fix
(owner follow-up item 1, 2026-10-27): each canary run now gets a FRESH
per-run store (canary_p{pi}/{h}) and raw_outputs are sliced per question.
CRITERION: two back-to-back canary runs give the SAME fingerprint.
Run on the RTX reference stand (llama-server :8085, Vulkan1); no iGPU
involvement. Diagnostic only: the canary is a regime label, not permission
(proposal v0.4)."""
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from run_stand2_panel12 import DATA, canary_fingerprint, LLM_BASE_URL, MODEL


def main():
    data = json.loads(DATA.read_text())
    by8 = {q["question_id"].split("_")[-1]: q for q in data}
    n_runs = int(os.environ.get("CANARY_CHECK_RUNS", "2"))
    runs = []
    for i in range(n_runs):
        t0 = time.time()
        c = canary_fingerprint(by8, i)
        dt = round(time.time() - t0, 1)
        runs.append({"run": i + 1, "canary_fp": c["canary_fp"],
                     "canary_facts": c["canary_facts"], "elapsed_s": dt,
                     "raw_calls": {h: len(c["canary_raw"][h])
                                   for h in c["canary_raw"]}})
        print(f"CANARY run {i + 1}/{n_runs}: fp={c['canary_fp'][:16]} "
              f"facts={c['canary_facts']} t={dt}s", flush=True)
    fps = {r["canary_fp"] for r in runs}
    ok = len(fps) == 1
    out = {
        "provenance": {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "purpose": "RTX-stand verification of the canary harness fix: "
                       "fresh store per canary run, raw_outputs sliced per "
                       "question; criterion = two back-to-back runs give the "
                       "same fingerprint",
            "runner": "evals/run_stand2_panel12.py (canary path, fixed "
                      "2026-10-27)",
            "server": LLM_BASE_URL, "model": MODEL,
            "canary": "311778f1, faba32e5, e47becba (proposal v0.4)",
        },
        "runs": runs,
        "all_same_fp": ok,
        "verdict": ("canary fix VERIFIED on RTX stand: back-to-back runs give "
                    "the same fingerprint" if ok else
                    "MISMATCH: canary fingerprints differ across back-to-back "
                    "runs"),
    }
    outname = os.environ.get("CANARY_CHECK_OUT", "stand2_canary_fix_check.json")
    Path("evals/results").joinpath(outname).write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(out["verdict"], flush=True)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
