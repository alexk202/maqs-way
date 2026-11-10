#!/usr/bin/env python3
"""Generic two-arm comparative runner (fixture-driven stand, twoarm-v1).

One experiment = one fixture. This file holds no experiment values: probe
texts, store records, the mechanism's note text, prompt assembly, seed scheme,
counts and the decision rule all come from the fixture JSON, validated against
fixtures/fixture-schema.json before anything runs. Adding a next experiment
means adding a fixture, not editing this runner.

Usage (stand convention, evals/eval_config.py supplies the server):
    python3 evals/twoarm_runner.py evals/fixtures/<id>.json --controls
    python3 evals/twoarm_runner.py evals/fixtures/<id>.json --main

Order of operations (pre-registration §8; not negotiable):
    runner written -> sha256 of prereg/fixture/schema/runner -> owner signature
    -> commit -> --controls -> report throughput and STOP (G-budget) -> owner
    confirmation -> --main -> artifact.

What --controls does: runs only fixture.controls cells (positive control and
empty-store sanity), checks G-arms/G-posctl/G-empty, writes
results/<fixture_id>_controls.json and prints the throughput estimate, then
stops. No verdict artifact is written by this mode.

What --main does: requires the controls file (same fixture sha256), re-checks
G-arms/G-config, runs every main cell, scores answers by the fixture's
pre-registered primary rule, computes Wilson intervals and the verdict exactly
as the fixture's decision_rule states, and writes:
    results/<fixture_id>_report.json   (config, cells, arms, gates, verdict)
    results/<fixture_id>_answers.jsonl (every answer, verbatim, one line/run)
    results/<fixture_id>_run_log.txt   (appended log)
The secondary subjective pass is NOT run here: subjective_paraphrase is null.

Gates (§3 of the pre-registration):
    G-fixture  fixture validates against the schema -> else exit, no run
    G-arms     prompts differ by the note block only, byte-for-byte
    G-posctl   positive control rate >= fixture threshold -> else VOID
    G-empty    empty store yields zero matches -> else run invalid
    G-config   every required config field recorded -> else exit, no run
    G-budget   after controls: print measured throughput and STOP
"""
import argparse
import hashlib
import json
import os
import platform
import re
import subprocess
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
FIXTURES = HERE / "fixtures"
SCHEMA_PATH = FIXTURES / "fixture-schema.json"
RESULTS = HERE / "results"

# P8 lesson (2026-11-09): an exported provider variable can silently redirect
# the client mid-run (mem0's OpenAI wrapper prefers OPENROUTER_API_KEY over the
# configured base URL). Scrubbed before any client import, same list as
# repro/run.sh; the fact is recorded in the artifact.
PROVIDER_ENV = ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "OPENAI_BASE_URL",
                "ANTHROPIC_API_KEY", "AZURE_OPENAI_API_KEY", "GOOGLE_API_KEY",
                "GEMINI_API_KEY", "DEEPSEEK_API_KEY")
ENV_AT_START = {name: name in os.environ for name in PROVIDER_ENV}
for _name in PROVIDER_ENV:
    os.environ.pop(_name, None)

from eval_config import LLM_API_KEY, LLM_BASE_URL, LLM_MODEL  # noqa: E402
from openai import OpenAI  # noqa: E402
import jsonschema  # noqa: E402


# --------------------------------------------------------------------------
# fixture handling
# --------------------------------------------------------------------------
def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 22), b""):
            h.update(chunk)
    return h.hexdigest()


def load_fixture(path):
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def validate_fixture(fixture, schema_path=SCHEMA_PATH):
    """G-fixture. Raises on invalid; the caller refuses to run."""
    with open(schema_path, encoding="utf-8") as fh:
        schema = json.load(fh)
    jsonschema.Draft202012Validator(schema).validate(fixture)


def arms_by_mode(fixture):
    on = [a for a in fixture["arms"] if a["mechanism_on"]]
    off = [a for a in fixture["arms"] if not a["mechanism_on"]]
    if len(on) != 1 or len(off) != 1:
        raise SystemExit("fixture must have exactly one arm with mechanism_on "
                         "true and one with false")
    return on[0], off[0]


def probe_by_id(fixture):
    return {p["probe_id"]: p for p in fixture["probes"]}


# --------------------------------------------------------------------------
# prompt assembly (fixture.prompt_assembly; nothing experiment-specific here)
# --------------------------------------------------------------------------
def memory_block(fixture, arm, records):
    """Mechanism realisation + header + formatted records; empty if no records.

    The note is placed per prompt_assembly.note_position (the schema allows
    'before_memory_header' only) and only when the arm has the mechanism on.
    With an empty store there is no block at all: the item's compliant
    behaviour is 'return nothing', and the empty-store cell is its reference.
    """
    pa = fixture["prompt_assembly"]
    if not records:
        return ""
    if pa["note_position"] != "before_memory_header":
        raise SystemExit(f"unsupported note_position: {pa['note_position']}")
    lines = []
    if arm["mechanism_on"]:
        lines.append(fixture["mechanism"]["realization"])
    lines.append(pa["memory_header"])
    for rec in records:
        lines.append(pa["record_format"].replace("{text}", rec["text"]))
    return "\n".join(lines)


def build_prompt(fixture, arm, probe, records):
    """Chat prompt: system = prompt_assembly.system (+ memory block), user =
    probe.query verbatim. The memory block lives in the system context so the
    user turn stays exactly the fixture's query; the whole prompt is recorded
    in the artifact (prompts_first_run) so nothing about the assembly is
    implicit."""
    pa = fixture["prompt_assembly"]
    block = memory_block(fixture, arm, records)
    system = pa["system"] if not block else pa["system"] + "\n\n" + block
    return {
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": probe["query"]},
        ],
        "system": system,
        "user": probe["query"],
        "memory_block": block,
    }


def check_arms(fixture):
    """G-arms: for every offtopic probe the ON arm equals the OFF arm after
    removing the note line, byte-for-byte, and the user turn is identical."""
    on, off = arms_by_mode(fixture)
    note = fixture["mechanism"]["realization"] + "\n"
    rows = []
    ok = True
    for probe in fixture["probes"]:
        if probe["role"] != "offtopic":
            continue
        a = build_prompt(fixture, on, probe, fixture["store"])
        b = build_prompt(fixture, off, probe, fixture["store"])
        a_sys = a["system"]
        stripped = a_sys.replace(note, "", 1)
        note_once = a_sys.count(note) == 1
        same_user = a["user"] == b["user"]
        same_after = stripped == b["system"]
        probe_ok = note_once and same_user and same_after
        ok = ok and probe_ok
        rows.append({"probe_id": probe["probe_id"], "ok": probe_ok,
                     "note_occurs_once": note_once,
                     "user_turn_identical": same_user,
                     "on_equals_off_after_removing_note": same_after,
                     "system_len_on": len(a_sys), "system_len_off": len(b["system"])})
    return {"ok": ok, "per_probe": rows,
            "method": "remove the note line from the ON-arm system message, "
                      "compare with the OFF-arm system message byte-for-byte; "
                      "user turns must be identical"}


# --------------------------------------------------------------------------
# cells and seeds (fixture.sampling.seed_scheme)
# --------------------------------------------------------------------------
def main_cells(fixture):
    """Cells in fixture order over (arm, probe) pairs the probe's run_in
    allows; arms as listed, probes as listed; cell_index from 0; offtopic
    probes only (positive-control probes have their own cell in controls)."""
    on, off = arms_by_mode(fixture)  # validates arm shape
    cells = []
    idx = 0
    for arm in fixture["arms"]:
        for probe in fixture["probes"]:
            if probe["role"] != "offtopic":
                continue
            if arm["arm_id"] not in probe["run_in"]:
                continue
            runs = fixture["runs_per_cell"]
            cells.append({
                "cell_index": idx, "arm": arm["arm_id"],
                "probe": probe["probe_id"],
                "mechanism_on": arm["mechanism_on"],
                "runs": runs, "store": "full",
                "seeds": [1000 * idx + r for r in range(1, runs + 1)],
            })
            idx += 1
    return cells


def control_cells(fixture):
    """Controls run after every main cell; their cell_index continues the
    enumeration so control seeds are deterministic too and cannot collide with
    main seeds. The scheme is recorded in the artifact."""
    start = len(main_cells(fixture))
    out = []
    for k, key in enumerate(("positive_control", "empty_store")):
        c = fixture["controls"][key]
        idx = start + k
        runs = c["runs"]
        out.append({
            "cell_index": idx, "arm": c["arm"], "probe": c["probe"],
            "mechanism_on": any(a["arm_id"] == c["arm"] and a["mechanism_on"]
                                for a in fixture["arms"]),
            "runs": runs,
            "store": "empty" if key == "empty_store" else "full",
            "seeds": [1000 * idx + r for r in range(1, runs + 1)],
            "role": key,
        })
    return out


def check_seed_example(fixture, cells):
    """Compare the computed seeds with fixture.sampling.seed_example, when the
    example is machine-readable. Unparsed examples are recorded, not fatal."""
    example = fixture["sampling"].get("seed_example", "")
    pat = re.compile(r"cell\s+(\d+)\s*=\s*\(([^,]+),\s*([^)]+)\):\s*seeds\s+(\d+)\.\.(\d+)")
    parsed = [{"cell_index": int(m.group(1)), "arm": m.group(2).strip(),
               "probe": m.group(3).strip(),
               "first": int(m.group(4)), "last": int(m.group(5))}
              for m in pat.finditer(example)]
    by_index = {c["cell_index"]: c for c in cells}
    checks = []
    for p in parsed:
        c = by_index.get(p["cell_index"])
        ok = bool(c) and c["arm"] == p["arm"] and c["probe"] == p["probe"] \
            and c["seeds"][0] == p["first"] and c["seeds"][-1] == p["last"]
        checks.append({**p, "ok": ok})
    return {"example": example, "parsed": checks,
            "ok": bool(checks) and all(c["ok"] for c in checks)}


# --------------------------------------------------------------------------
# stand config (eval_config convention) + server facts (CONFIG-ASSERT §2)
# --------------------------------------------------------------------------
def _http_json(url, timeout=10):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.load(r)


def server_props():
    root = LLM_BASE_URL.rsplit("/v1", 1)[0]
    try:
        return _http_json(f"{root}/props")
    except Exception as e:  # foreign OpenAI-compatible server
        return {"_error": f"{type(e).__name__}: {e}"}


def server_models():
    try:
        return _http_json(f"{LLM_BASE_URL}/models")
    except Exception as e:
        return {"_error": f"{type(e).__name__}: {e}"}


def gpu_facts():
    """Device/driver from nvidia-smi; recorded as a list of raw rows. Absence is
    a missing field -> G-config refuses the run (the stand must have a GPU)."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,driver_version",
             "--format=csv,noheader"],
            capture_output=True, text=True, timeout=20)
        rows = [l.strip() for l in out.stdout.splitlines() if l.strip()]
        return rows or None
    except Exception:
        return None


def collect_config(fixture, fixture_path, cells):
    """Every §2 field, from the live stand, not from a belief about it."""
    props = server_props()
    models = server_models()
    model_path = props.get("model_path")
    model_sha = None
    model_size = None
    if model_path and os.path.isfile(model_path):
        model_sha = sha256_file(model_path)
        model_size = os.path.getsize(model_path)
    served = None
    if isinstance(models, dict) and models.get("models"):
        served = models["models"][0].get("model") or models["models"][0].get("name")
    dgs = props.get("default_generation_settings", {}) or {}
    params = dgs.get("params", {}) or {}
    cfg = {
        "runner": "evals/twoarm_runner.py",
        "server": {"base_url": LLM_BASE_URL,
                   "build_info": props.get("build_info"),
                   "version": served,
                   "model_alias": props.get("model_alias"),
                   "total_slots": props.get("total_slots"),
                   "props_available": "_error" not in props,
                   "props_error": props.get("_error"),
                   "models_error": models.get("_error") if isinstance(models, dict) else None,
                   "server_defaults": {k: params.get(k) for k in
                                       ("seed", "temperature", "top_p", "repeat_penalty",
                                        "top_k", "n_ctx") if k in params}},
        "model": {"path": model_path, "sha256": model_sha, "size_bytes": model_size,
                  "name_requested": LLM_MODEL, "name_served": served},
        "context": {"n_ctx": dgs.get("n_ctx")},
        "sampling": {"temperature": fixture["sampling"]["temperature"],
                     "top_p": fixture["sampling"]["top_p"],
                     "max_tokens": fixture["sampling"]["max_tokens"],
                     "seed_scheme": fixture["sampling"]["seed_scheme"],
                     "seed_example": fixture["sampling"].get("seed_example"),
                     "control_seed_scheme":
                         "control cells continue the cell_index enumeration after "
                         "all main cells; seed = 1000 * cell_index + run_index",
                     "seeds_by_cell": [{"cell_index": c["cell_index"],
                                        "arm": c["arm"], "probe": c["probe"],
                                        "seeds": c["seeds"]} for c in cells]},
        "environment": {"uname": " ".join(os.uname()),
                        "python": platform.python_version(),
                        "gpu": gpu_facts()},
        "fixture": {"path": str(fixture_path), "sha256": sha256_file(fixture_path),
                    "id": fixture["fixture_id"],
                    "version": fixture["fixture_version"],
                    "schema_path": str(SCHEMA_PATH),
                    "schema_sha256": sha256_file(SCHEMA_PATH)},
        "prereg": {"path": None, "sha256": None},
        "runner": {"path": str(Path(__file__).resolve()),
                   "sha256": sha256_file(Path(__file__).resolve())},
        "provider_env_scrubbed": ENV_AT_START,
        "context_isolation": {
            "method": "stateless chat/completions request per generation, a "
                      "fresh messages array every time, cache_prompt=false "
                      "(llama.cpp prompt cache disabled per request); no "
                      "conversation, slot or KV state is carried between runs",
            "slot_erase": "POST /slots/{id}?action=erase is NOT used: this "
                          "server answers 501 without --slot-save-path; with "
                          "cache_prompt=false the prompt is re-evaluated for "
                          "every request",
            "fixture_statement": fixture["prompt_assembly"]["context_isolation"],
        },
    }
    prereg = HERE / f"prereg-{fixture['fixture_id']}.md"
    if prereg.is_file():
        cfg["prereg"] = {"path": str(prereg), "sha256": sha256_file(prereg)}
    return cfg


def config_missing(cfg):
    """G-config: the fields §2 of the pre-registration demands. Missing any ->
    the runner stops before generating."""
    missing = []
    for path in (("model", "path"), ("model", "sha256"),
                 ("server", "build_info"), ("server", "version"),
                 ("context", "n_ctx"), ("sampling", "temperature"),
                 ("sampling", "top_p"), ("sampling", "max_tokens"),
                 ("sampling", "seed_scheme"), ("environment", "uname"),
                 ("environment", "python"), ("environment", "gpu"),
                 ("fixture", "sha256"), ("fixture", "schema_sha256"),
                 ("prereg", "sha256"), ("runner", "sha256")):
        node = cfg
        for key in path:
            node = node.get(key) if isinstance(node, dict) else None
        # a falsy numeric (temperature 0.0, n_ctx 0) is a value, not an absence
        if node is None or (isinstance(node, (str, list)) and not node):
            missing.append(".".join(path))
    if not cfg["sampling"]["seeds_by_cell"]:
        missing.append("sampling.seeds_by_cell")
    return missing


# --------------------------------------------------------------------------
# generation and scoring
# --------------------------------------------------------------------------
def make_client():
    return OpenAI(api_key=LLM_API_KEY or "local", base_url=LLM_BASE_URL,
                  timeout=180, max_retries=2)


def generate(client, fixture, prompt, seed):
    """One isolated generation. cache_prompt=false keeps the server from
    reusing KV/prompt state across runs (§2 context isolation)."""
    t0 = time.perf_counter()
    resp = client.chat.completions.create(
        model=LLM_MODEL,
        messages=prompt["messages"],
        temperature=fixture["sampling"]["temperature"],
        top_p=fixture["sampling"]["top_p"],
        max_tokens=fixture["sampling"]["max_tokens"],
        seed=seed,
        extra_body={"cache_prompt": False},
    )
    dt = time.perf_counter() - t0
    choice = resp.choices[0]
    text = choice.message.content or ""
    return {"text": text,
            "finish_reason": choice.finish_reason,
            "truncated": choice.finish_reason == "length",
            "duration_s": round(dt, 3),
            "usage": resp.usage.model_dump() if getattr(resp, "usage", None) else None}


def score_answer(answer, records, case_insensitive):
    """Primary rule: marker OR closed vocabulary of a record, substring,
    optionally case-insensitive; one run counts once if any record matched."""
    hay = answer.lower() if case_insensitive else answer
    matched = []
    for rec in records:
        marker = rec["marker"].lower() if case_insensitive else rec["marker"]
        hit = bool(marker) and marker in hay
        if not hit:
            for word in rec["vocabulary"]:
                w = word.lower() if case_insensitive else word
                if w and w in hay:
                    hit = True
                    break
        if hit:
            matched.append(rec["record_id"])
    return matched


def wilson(k, n, confidence):
    """Wilson score interval without external dependencies."""
    if n == 0:
        return [None, None]
    from statistics import NormalDist
    z = NormalDist().inv_cdf(1 - (1 - confidence) / 2)
    p = k / n
    den = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / den
    half = z * ((p * (1 - p) / n + z * z / (4 * n * n)) ** 0.5) / den
    return [round(centre - half, 6), round(centre + half, 6)]


def run_cell(client, fixture, cell, records, answers_sink=None, label=""):
    """Run one cell; optionally stream every answer to the JSONL sink."""
    on_arm = {"arm_id": cell["arm"], "mechanism_on": cell["mechanism_on"]}
    probe = probe_by_id(fixture)[cell["probe"]]
    prompt = build_prompt(fixture, on_arm, probe, records)
    ci = fixture["scoring"]["primary"]["case_insensitive"]
    runs = []
    for run_index, seed in enumerate(cell["seeds"], start=1):
        gen = generate(client, fixture, prompt, seed)
        answer = gen["text"]
        matched = score_answer(answer, records, ci)
        row = {"cell": f"{cell['arm']}/{cell['probe']}",
               "cell_index": cell["cell_index"], "arm": cell["arm"],
               "probe": cell["probe"], "role": cell.get("role", "main"),
               "run_index": run_index, "seed": seed, "answer": answer,
               "matched_records": matched, "matched": bool(matched),
               "truncated": gen["truncated"],
               "finish_reason": gen["finish_reason"],
               "duration_s": gen["duration_s"], "usage": gen["usage"]}
        runs.append(row)
        if answers_sink is not None:
            answers_sink.write(json.dumps(row, ensure_ascii=False) + "\n")
            answers_sink.flush()
        if run_index % 10 == 0 or run_index == len(cell["seeds"]):
            hits = sum(1 for r in runs if r["matched"])
            print(f"  {label}{cell['arm']}/{cell['probe']} "
                  f"{run_index}/{len(cell['seeds'])} matches={hits} "
                  f"{gen['duration_s']:.1f}s", flush=True)
    matches = sum(1 for r in runs if r["matched"])
    n = len(runs)
    rate = matches / n if n else 0.0
    conf = fixture["decision_rule"]["confidence"]
    return {"cell": f"{cell['arm']}/{cell['probe']}",
            "cell_index": cell["cell_index"], "arm": cell["arm"],
            "probe": cell["probe"], "role": cell.get("role", "main"),
            "store": cell["store"], "runs": n, "matches": matches,
            "rate": round(rate, 6), "wilson": wilson(matches, n, conf),
            "truncated": sum(1 for r in runs if r["truncated"]),
            "mean_s": round(sum(r["duration_s"] for r in runs) / n, 3) if n else None,
            "seeds": cell["seeds"],
            "prompt_first_run": {"system": prompt["system"], "user": prompt["user"]},
            "answers": runs}


# --------------------------------------------------------------------------
# modes
# --------------------------------------------------------------------------
def load_and_validate(fixture_path):
    fixture = load_fixture(fixture_path)
    try:
        validate_fixture(fixture)
    except jsonschema.ValidationError as e:
        print(f"G-fixture FAILED: fixture does not validate against "
              f"{SCHEMA_PATH}: {e.message}", file=sys.stderr)
        raise SystemExit(2)
    return fixture


def cmd_controls(fixture, fixture_path):
    print(f"G-fixture ok: {fixture_path} validates against {SCHEMA_PATH}")
    g_arms = check_arms(fixture)
    print(f"G-arms: {'ok' if g_arms['ok'] else 'FAILED'} "
          f"({len(g_arms['per_probe'])} offtopic probes)")
    if not g_arms["ok"]:
        print("G-arms FAILED: arms differ by more than the note block; run is "
              "not valid, not running controls", file=sys.stderr)
        return 4

    cells = control_cells(fixture)
    all_cells = main_cells(fixture) + cells
    cfg = collect_config(fixture, fixture_path, all_cells)
    missing = config_missing(cfg)
    if missing:
        print("G-config FAILED, missing fields: " + ", ".join(missing), file=sys.stderr)
        return 3

    client = make_client()
    print(f"server: {LLM_BASE_URL} build={cfg['server']['build_info']} "
          f"model={cfg['model']['name_served']} n_ctx={cfg['context']['n_ctx']}")
    out_cells = []
    for cell in cells:
        records = fixture["store"] if cell["store"] == "full" else []
        print(f"control cell {cell['cell_index']} ({cell['role']}): "
              f"{cell['arm']}/{cell['probe']} store={cell['store']} "
              f"runs={cell['runs']}", flush=True)
        out_cells.append(run_cell(client, fixture, cell, records,
                                  label="control "))

    pos = next(c for c in out_cells if c["role"] == "positive_control")
    emp = next(c for c in out_cells if c["role"] == "empty_store")
    min_rate = fixture["controls"]["positive_control"]["min_rate"]
    pos_ok = pos["rate"] >= min_rate
    empty_matches = emp["matches"]
    empty_ok = empty_matches == 0
    main_runs = sum(c["runs"] for c in main_cells(fixture))
    durations = [a["duration_s"] for c in out_cells for a in c["answers"]]
    mean_s = sum(durations) / len(durations) if durations else 0.0
    expected_main_s = round(mean_s * main_runs, 1) if main_runs else None

    gates = {"G-fixture": "ok", "G-arms": g_arms, "G-config": {"missing": []},
             "G-posctl": {"rate": pos["rate"], "min_rate": min_rate,
                          "ok": pos_ok},
             "G-empty": {"matches": empty_matches, "ok": empty_ok}}
    summary = {
        "created": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "fixture_id": fixture["fixture_id"],
        "fixture_sha256": cfg["fixture"]["sha256"],
        "schema_sha256": cfg["fixture"]["schema_sha256"],
        "prereg_sha256": cfg["prereg"]["sha256"],
        "runner_sha256": cfg["runner"]["sha256"],
        "config": cfg,
        "gates": gates,
        "cells": [{k: v for k, v in c.items() if k != "answers"} for c in out_cells],
        "answers": [{k: v for k, v in a.items() if k != "usage"}
                    for c in out_cells for a in c["answers"]],
        "mean_generation_s": round(mean_s, 3),
        "main_runs": main_runs,
        "expected_main_s": expected_main_s,
    }
    RESULTS.mkdir(exist_ok=True)
    (RESULTS / f"{fixture['fixture_id']}_controls.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False))
    log = (f"\n=== {summary['created']} CONTROLS {fixture['fixture_id']} "
           f"fixture_sha256={cfg['fixture']['sha256'][:16]} ===\n"
           f"G-arms ok; G-posctl rate={pos['rate']} (min {min_rate}) ok={pos_ok}; "
           f"G-empty matches={empty_matches} ok={empty_ok}\n"
           f"mean generation {mean_s:.2f}s; main runs {main_runs}; "
           f"expected main ~{expected_main_s}s\n")
    with open(RESULTS / f"{fixture['fixture_id']}_run_log.txt", "a") as fh:
        fh.write(log)
    print()
    print(f"positive control (c1, {pos['arm']}): "
          f"{pos['matches']}/{pos['runs']} = {pos['rate']:.3f} "
          f"(threshold {min_rate}) -> {'ok' if pos_ok else 'VOID'}")
    print(f"empty store (p1, {emp['arm']}): matches={empty_matches} "
          f"-> {'ok' if empty_ok else 'INVALID'}")
    print(f"mean generation time: {mean_s:.2f} s")
    print(f"expected duration of {main_runs} main runs: ~{expected_main_s:.0f} s "
          f"(~{expected_main_s/60:.1f} min)")
    if not pos_ok:
        print("G-posctl FAILED: pipeline is broken; run is VOID. Not continuing.",
              file=sys.stderr)
        return 5
    if not empty_ok:
        print("G-empty FAILED: the scoring rule fires with an empty store; "
              "run is invalid. Not continuing.", file=sys.stderr)
        return 6
    print("STOP (G-budget): main cells are NOT run without owner confirmation.")
    return 0


def homogeneity(fixture, cell_results):
    """§5: within each arm every per-probe rate must fall inside that arm's
    pooled Wilson interval; otherwise the pooled verdict is withheld."""
    on, off = arms_by_mode(fixture)
    out = {}
    ok_all = True
    for arm in (on, off):
        rows = [c for c in cell_results if c["arm"] == arm["arm_id"]]
        k = sum(c["matches"] for c in rows)
        n = sum(c["runs"] for c in rows)
        pooled = wilson(k, n, fixture["decision_rule"]["confidence"])
        per = {c["probe"]: c["rate"] for c in rows}
        inside = {p: (pooled[0] is not None and pooled[0] <= r <= pooled[1])
                  for p, r in per.items()}
        ok = all(inside.values())
        ok_all = ok_all and ok
        out[arm["arm_id"]] = {"n": n, "matches": k,
                              "rate": round(k / n, 6), "wilson": pooled,
                              "per_probe": per, "inside_pooled": inside, "ok": ok}
    return {"ok": ok_all, "arms": out}


def decide(fixture, hom):
    """Verdict strictly per fixture.decision_rule; computed, not interpreted."""
    on, off = arms_by_mode(fixture)
    a = hom["arms"][on["arm_id"]]
    b = hom["arms"][off["arm_id"]]
    base = {"method": fixture["decision_rule"]["method"],
            "confidence": fixture["decision_rule"]["confidence"],
            "direction_definition": fixture["decision_rule"]["direction_definition"],
            "on_arm": on["arm_id"], "off_arm": off["arm_id"],
            "on_upper": a["wilson"][1], "off_lower": b["wilson"][0],
            "homogeneity_ok": hom["ok"]}
    if not hom["ok"]:
        return {**base, "outcome": "no_pooled_verdict",
                "detail": "homogeneity check failed: at least one per-probe rate "
                          "falls outside its arm's pooled Wilson interval; the "
                          "result is reported per probe only, with no statement "
                          "about the mechanism overall"}
    if a["wilson"][1] < b["wilson"][0]:
        return {**base, "outcome": "nonoverlap_on_below_off",
                "detail": f"upper({on['arm_id']})={a['wilson'][1]} < "
                          f"lower({off['arm_id']})={b['wilson'][0]}; intervals "
                          f"do not overlap and the ON arm is below the OFF arm"}
    return {**base, "outcome": "overlap",
            "detail": "Wilson intervals overlap; per the pre-registration the "
                      "item's current wording stands",
            "prereg_statement": fixture["decision_rule"]["on_overlap"]}


def cmd_main(fixture, fixture_path):
    print(f"G-fixture ok: {fixture_path} validates against {SCHEMA_PATH}")
    g_arms = check_arms(fixture)
    if not g_arms["ok"]:
        print("G-arms FAILED: arms differ by more than the note block; run is "
              "not valid", file=sys.stderr)
        return 4
    cells = main_cells(fixture)
    all_cells = main_cells(fixture) + control_cells(fixture)
    cfg = collect_config(fixture, fixture_path, all_cells)
    missing = config_missing(cfg)
    if missing:
        print("G-config FAILED, missing fields: " + ", ".join(missing), file=sys.stderr)
        return 3
    seed_check = check_seed_example(fixture, main_cells(fixture))
    controls_path = RESULTS / f"{fixture['fixture_id']}_controls.json"
    if not controls_path.is_file():
        print(f"controls evidence missing ({controls_path}); run --controls "
              f"first (pre-registration §8 order)", file=sys.stderr)
        return 7
    controls = json.loads(controls_path.read_text())
    if controls.get("fixture_sha256") != cfg["fixture"]["sha256"]:
        print("controls evidence belongs to a different fixture sha256; refusing "
              "to mix runs", file=sys.stderr)
        return 7
    if not (controls["gates"]["G-posctl"]["ok"] and controls["gates"]["G-empty"]["ok"]):
        print("controls gates are not green in the stored evidence; run is "
              "invalid", file=sys.stderr)
        return 7

    client = make_client()
    print(f"server: {LLM_BASE_URL} build={cfg['server']['build_info']} "
          f"model={cfg['model']['name_served']} n_ctx={cfg['context']['n_ctx']}")
    print(f"seed example check: {'ok' if seed_check['ok'] else 'MISMATCH'}")

    answers_path = RESULTS / f"{fixture['fixture_id']}_answers.jsonl"
    answers_path.write_text("")  # fresh file; one JSON line per run
    cells_out = []
    t_start = time.time()
    with open(answers_path, "a", encoding="utf-8") as sink:
        for i, cell in enumerate(cells, start=1):
            print(f"cell {i}/{len(cells)}: {cell['arm']}/{cell['probe']} "
                  f"runs={cell['runs']}", flush=True)
            res = run_cell(client, fixture, cell, fixture["store"], answers_sink=sink)
            cells_out.append(res)
            print(f"  -> {res['matches']}/{res['runs']} = {res['rate']:.3f} "
                  f"wilson={res['wilson']} truncated={res['truncated']}",
                  flush=True)
    total_s = round(time.time() - t_start, 1)

    hom = homogeneity(fixture, cells_out)
    verdict = decide(fixture, hom)
    report = {
        "provenance": {
            "date": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
            "runner": "evals/twoarm_runner.py",
            "fixture_id": fixture["fixture_id"],
            "fixture_version": fixture["fixture_version"],
            "prereg": cfg["prereg"],
            "note": "single run of a fixture; statistical reproduction only, "
                    "byte-level reproduction is impossible by design",
        },
        "config": cfg,
        "gates": {"G-fixture": "ok", "G-arms": g_arms,
                  "G-config": {"missing": []},
                  "G-posctl": controls["gates"]["G-posctl"],
                  "G-empty": controls["gates"]["G-empty"],
                  "G-budget": {"controls_evidence": str(controls_path),
                               "mean_generation_s": controls["mean_generation_s"],
                               "main_runs": controls["main_runs"],
                               "expected_main_s": controls["expected_main_s"]},
                  "G-seed-example": seed_check},
        "controls": controls["cells"],
        "cells": [{k: v for k, v in c.items()
                   if k not in ("answers", "prompt_first_run")} for c in cells_out],
        "prompts_first_run": {c["cell"]: c["prompt_first_run"] for c in cells_out},
        "arms": hom["arms"],
        "homogeneity": hom,
        "verdict": verdict,
        "subjective_paraphrase": None,
        "total_wall_clock_s": total_s,
    }
    (RESULTS / f"{fixture['fixture_id']}_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False))
    with open(RESULTS / f"{fixture['fixture_id']}_run_log.txt", "a") as fh:
        fh.write(f"\n=== {report['provenance']['date']} MAIN {fixture['fixture_id']} "
                 f"fixture_sha256={cfg['fixture']['sha256'][:16]} ===\n")
        for c in cells_out:
            fh.write(f"{c['cell']}: {c['matches']}/{c['runs']} rate={c['rate']} "
                     f"wilson={c['wilson']} truncated={c['truncated']}\n")
        fh.write(f"homogeneity ok={hom['ok']}; verdict={verdict['outcome']}\n"
                 f"wall clock {total_s}s\n")
    print()
    for c in cells_out:
        print(f"{c['cell']}: {c['matches']}/{c['runs']} = {c['rate']:.3f} "
              f"wilson={c['wilson']} truncated={c['truncated']}")
    for arm, d in hom["arms"].items():
        print(f"{arm}: {d['matches']}/{d['n']} = {d['rate']:.3f} wilson={d['wilson']}")
    print(f"homogeneity: {'ok' if hom['ok'] else 'FAILED'}")
    print(f"verdict: {verdict['outcome']} -- {verdict['detail']}")
    print(f"artifact: {RESULTS / (fixture['fixture_id'] + '_report.json')}")
    return 0


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("fixture", help="path to a twoarm-v1 fixture JSON")
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--controls", action="store_true",
                      help="run control cells only, then stop (G-budget)")
    mode.add_argument("--main", action="store_true",
                      help="run main cells after controls and write the artifact")
    args = ap.parse_args(argv)
    fixture_path = Path(args.fixture)
    if not fixture_path.is_absolute():
        fixture_path = Path.cwd() / fixture_path
    fixture = load_and_validate(fixture_path)
    if args.controls:
        return cmd_controls(fixture, fixture_path)
    return cmd_main(fixture, fixture_path)


if __name__ == "__main__":
    sys.exit(main())
