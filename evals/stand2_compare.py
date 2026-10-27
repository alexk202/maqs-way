#!/usr/bin/env python3
"""Stand-2 determinism verdict builder (prereg-stand2-igpu.md).

Compares the two invocation artifacts of run_stand2_panel12.py:
  - invocation A (STAND2_PASSES=2): pass 1 vs pass 2 back-to-back;
  - across restart: A passes vs invocation B (STAND2_PASSES=1, pass 3).

CRITERION (pre-registered): pass1 == pass2 AND pass3 == pass1/pass2, per
question, on ALL of raw extraction outputs, stored texts, frames.

Comparison with the RTX reference stand is RECORDED AS FACT ONLY (match
counts of raw outputs against the available RTX panel artifacts), NOT a
criterion. Any divergence is recorded as-is, no interpretation beyond the
data.

Usage: stand2_compare.py <A.json> <B.json> [--rtx file1,file2,...]
Writes results/stand2_igpu_determinism_check.json and prints a summary.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

OUT = Path(__file__).resolve().parent / "results"


def by8_of_pass(pass_entry):
    return {r["q_id"].split("_")[-1]: r for r in pass_entry["results"]}


def compare_passes(p1, p2):
    a, b = by8_of_pass(p1), by8_of_pass(p2)
    rows, ident = [], 0
    for h in ["75832dbd", "0a34ad58", "1faac195", "b0479f84",
              "fca70973", "311778f1", "afdc33df", "19b5f2b3",
              "e47becba", "58bf7951", "3b6f954b", "faba32e5"]:
        x, y = a[h], b[h]
        raw_eq = x["raw_outputs"] == y["raw_outputs"]
        st_eq = x["stored_texts"] == y["stored_texts"]
        fr_eq = x["frames"] == y["frames"]
        mem_eq = x["memory_texts"] == y["memory_texts"]
        ok = raw_eq and st_eq and fr_eq and mem_eq
        ident += ok
        rows.append({"q_id": x["q_id"], "raw_identical": raw_eq,
                     "stored_texts_identical": st_eq,
                     "frames_identical": fr_eq,
                     "memory_texts_identical": mem_eq,
                     "byte_identical": ok,
                     "first_diff": ("" if raw_eq else _first_diff(
                         x["raw_outputs"], y["raw_outputs"]))})
    return ident, rows


def _first_diff(r1, r2):
    for i, (x, y) in enumerate(zip(r1, r2)):
        if x != y:
            n = min(len(x), len(y))
            j = next((k for k in range(n) if x[k] != y[k]), n)
            return f"call {i}, char {j}: {len(x)} vs {len(y)} chars"
    return f"call count {len(r1)} vs {len(r2)}"


def rtx_match(rows, rtx_path):
    art = json.loads(Path(rtx_path).read_text())
    rtx = {}
    for p in art["passes"]:
        for r in p["results"] if "results" in p else p:
            rtx[r["q_id"].split("_")[-1]] = r["raw_outputs"]
    out, n = {}, 0
    for row in rows:
        h = row["q_id"].split("_")[-1]
        eq = h in rtx and rtx[h] == row["_raw"]
        out[h] = eq
        n += eq
    return n, out


def main():
    a_path, b_path = sys.argv[1], sys.argv[2]
    rtx_files = []
    if "--rtx" in sys.argv:
        rtx_files = sys.argv[sys.argv.index("--rtx") + 1].split(",")
    A = json.loads(Path(a_path).read_text())
    B = json.loads(Path(b_path).read_text())
    assert len(A["passes"]) >= 2, "A needs >= 2 passes"

    within_ident, within_rows = compare_passes(A["passes"][0], A["passes"][1])
    for row in within_rows:
        row["_raw"] = by8_of_pass(A["passes"][0])[row["q_id"].split("_")[-1]]["raw_outputs"]

    cross_rows, cross_ident = [], None
    if len(B["passes"]) >= 1:
        # strip the helper key before writing
        cross_ident, cross_rows = compare_passes(
            A["passes"][0], B["passes"][0])
        for row in cross_rows:
            row.pop("_raw", None)
    for row in within_rows:
        row.pop("_raw", None)

    rtx = {}
    if rtx_files and cross_rows is not None:
        passA = by8_of_pass(A["passes"][0])
        for f in rtx_files:
            art = json.loads(Path(f).read_text())
            rtx_map = {}
            for p in art["passes"]:
                for r in (p["results"] if "results" in p else p):
                    rtx_map[r["q_id"].split("_")[-1]] = r["raw_outputs"]
            n = sum(1 for h, r in passA.items() if rtx_map.get(h) == r["raw_outputs"])
            rtx[f] = {"raw_match_vs_A_pass1": n, "of": 12}

    canaries = {tag: [p["header"]["canary"] for p in art["passes"]]
                for tag, art in (("A", A), ("B", B))}
    fp_set = {c["canary_fp"] for cs in canaries.values() for c in cs}

    out = {
        "provenance": {
            "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "artifact_A": a_path, "artifact_B": b_path,
            "stand": "stand-2 iGPU Vulkan0 (Intel Arc)",
            "criterion": "prereg-stand2-igpu.md: pass1==pass2 AND pass3==pass1 "
                         "(raw, stored, frames) on all 12 panel questions; "
                         "RTX comparison = fact only, not a criterion",
        },
        "within_A": {"identical": within_ident, "of": 12, "per_question": within_rows},
        "across_restart": {"identical": cross_ident, "of": 12, "per_question": cross_rows},
        "canary_fingerprints": canaries,
        "canary_all_same_fp": len(fp_set) == 1,
        "rtx_fact_only": rtx,
    }
    crit = (within_ident == 12 and cross_ident == 12)
    out["verdict"] = ("CRITERION MET: pass1==pass2 and pass3==pass1/2, "
                      "byte-identical (raw, stored, frames) on all 12"
                      if crit else
                      f"CRITERION NOT MET: within {within_ident}/12, "
                      f"across restart {cross_ident}/12 (raw, stored, frames)")
    (OUT / "stand2_igpu_determinism_check.json").write_text(
        json.dumps(out, indent=2, ensure_ascii=False))
    print(f"WITHIN A:        {within_ident}/12")
    print(f"ACROSS RESTART:  {cross_ident}/12")
    print(f"CANARY: all same fingerprint = {len(fp_set) == 1}")
    for f, r in rtx.items():
        print(f"RTX FACT vs {f}: {r['raw_match_vs_A_pass1']}/12")
    print(f"VERDICT: {out['verdict']}")
    return 0 if crit else 1


if __name__ == "__main__":
    sys.exit(main())
