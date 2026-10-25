# evals/REPRODUCE.md — the stand recipe for reproducing the runs

Canonical version (English). Russian mirror: [REPRODUCE-RU.md](REPRODUCE-RU.md).
Both are maintained in parallel; if they disagree, this file wins.

Goal: on a clean machine, from this file alone, without hints from the author —
bring the smoke run to the end. The acceptance criterion (adopted 2026-10-24):
smoke completes → the stand is assembled correctly; the full run comes after,
deliberately (~1 hour of GPU).

## 0. Honest reproducibility caveat (read before comparing numbers)

- **GPUs give a small variance even with `--seed 42` and `temperature=0`**
  (Vulkan arithmetic is nondeterministic; the project canon acknowledges this —
  see prereg-v03, "GPU nondeterminism acknowledged"). Measured on our stand:
  at T=0, 9 of 11 "empty" questions did not reproduce between runs.
- Therefore **numbers are compared in bands, not to the third decimal**: a
  foreign R@5 = 0.981 against our 0.987 is the same result; 0.929 against
  0.987 is a real difference. Guard thresholds belong to the project's preregs;
  for external comparison keep a band of ±0.01–0.02.
- Bands and class compositions (mal/trunc/loop) transfer between runs;
  per-question intersections are NOT interpreted (branch canon, Oct 2026).
- **Confound discovered 2026-10-25**: every run before the H5 guard (`ffb5879`)
  shared the live `~/.mem0/history.db` — a ≤10-message tail of the previous
  question/run entered every extraction prompt, and extracted facts were written
  to the live history store (forensics + measured impact:
  `results/history_confound_forensics.md`; disclosure:
  `results/history_confound_disclosure_note.md`).
- **A live example (from this very stand, recorded with an explanation)**: the
  old n=5 smoke with an answer-token proxy (substring/token coverage of the
  answer inside the top-5) scored 5/5 (Oct 16, pre-9177 build, ctx 16384, no
  seed) and 0/5 (Oct 24, build 9177, ctx 32768, seed 42) — **an artifact of a
  fragile n=5 proxy metric, not a stand regression**: the full single-156 slice
  held evidence-R@5 = 0.994 the same day on the same servers. Lesson accepted:
  the smoke now uses the same evidence-R@5 as the full run (expected value on
  a working stand: 5/5); the old proxy stays as a secondary diagnostic line
  and is NOT a metric.

## 1. Hardware

- GPU with ≥ 12 GB VRAM (our stand: RTX 5060 Ti 16 GB, Vulkan backend);
  live consumption: ~8.8 GB for the LLM server + ~0.2 GB for the embedder.
- Time: smoke n=5 ~5–10 min; full single-156 ~53–66 min (~24–40 s per question).

## 2. Python environment

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt   # exact versions; mem0 is a git pin of a commit
```

`requirements.txt` is frozen from the stand venv (34 packages). mem0 is
installed NOT from PyPI but as **an exact upstream commit** of
`mem0ai/mem0@0724291b…` (a clean detached checkout, no local modifications) —
it sits between 2.2.x releases; this is intentional, not a mistake.

## 3. LLM server

1. Build llama.cpp (our build: **9177, commit 366c5e2a**, Vulkan backend).
2. Download the model: `bartowski/Meta-Llama-3.1-8B-Instruct-GGUF`, file
   `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf`
   (`https://huggingface.co/bartowski/Meta-Llama-3.1-8B-Instruct-GGUF`),
   size 4,920,739,232 bytes, **md5 `6eb593f3f5eee264d6c60c186ccc12e0`** — verify it.
3. Launch (our stand; your `--device` may differ — check
   `llama-server --list-devices` and pick your discrete GPU):

```bash
llama-server -m Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf -c 32768 -ngl 99 \
  --device Vulkan1 --host 127.0.0.1 --port 8085 --seed 42
```

- `ctx 32768` and `--seed 42` are part of the methodology; do not change them.
- The server runs WITHOUT `--api-key`, so any bearer token works (the scripts
  substitute `local` themselves, see §5).
- This build's default `repeat_penalty` is 1.0 (disabled) — the base runs use
  it as-is; penalty-based loop treatment is a separate branch topic and is not
  part of reproducing the base runs.

## 4. Embedder

Any OpenAI-compatible embeddings server with `nomic-embed-text-v1.5`
(768 dimensions). Our stand: LM Studio
(`lms load text-embedding-nomic-embed-text-v1.5`, port 1449). A llama-server
with the GGUF build of nomic works too — what matters is that the model and
dimensionality match the variables of §5.

## 5. Environment variables (all default to the stand values — no need to set)

| Variable | Default | When to override |
|---|---|---|
| `LLM_BASE_URL` | `http://127.0.0.1:8085/v1` | different port / Ollama / LM Studio |
| `EMBED_BASE_URL` | `http://127.0.0.1:1449/v1` | different embedder server |
| `LLM_MODEL` | `Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf` | different model name in your server's API |
| `EMBED_MODEL` | `text-embedding-nomic-embed-text-v1.5` | different embedder |
| `EMBED_DIMS` | `768` | different dimensionality |
| `LLM_API_KEY` | contents of `LLM_API_KEY_FILE`, else `local` | server with authorization |
| `LLM_API_KEY_FILE` | `/tmp/opencode/pilot8085.key` | your stand's convention |
| `EMBED_API_KEY` | `local-smoke` | embedder with authorization |
| `EVAL_GUARD_PATHS` | (empty) | extra guarded roots, colon-separated (isolation guard, §6) |

There is **no need to create the key file**: if it is absent (and `LLM_API_KEY`
is not set), the scripts substitute `local` — a server without `--api-key`
accepts any bearer token.

One source of truth: `evals/eval_config.py` — all runners import from it;
there are no literal server addresses left in the run code.

## 6. Isolation guard (MAQS H5 [CRIT]) — built into every runner

Every runner (`run_single156_*`, probes, smoke pilots) wraps its `main()` with
`@guarded()` from `evals/isolation_guard.py`: the live-store roots are
snapshotted at import time (the guard is imported before `from mem0 import
Memory`, so import-time side effects are inside the guarded window), and after
the run body the same roots are re-read and compared. Any divergence prints
`[H5 isolation guard] RED` lines and forces exit code 1 — the verify step runs
even if the run body raised. This is an H5 extension of the MAQS [Unreleased]
line: the isolation guard executes in EVERY run, built into the runner, not
periodically.

- **Guarded roots** (live stores = anything outside the per-run temp store):
  `~/.mem0` (the mem0 default dir: `history.db`, `config.json`,
  `migrations_qdrant/` and anything else inside), `~/.local/share/qdrant`,
  `~/.cache/qdrant`, plus extra colon-separated roots from `EVAL_GUARD_PATHS`.
  Roots that do not exist are guarded as empty: anything created there during
  a run is a leaked artifact and turns the guard RED.
- **Comparison semantics**: SQLite files (`*.db` and friends) are compared by
  LOGICAL ROWS, never by md5 — a WAL checkpoint rewrites the main file bytes
  without any data change, so byte-hashing a live WAL base would false-RED
  (known checkpoint trap). The `-wal`/`-shm`/`-journal` side files are ignored
  as transient. Everything else is compared by sha256 of bytes. New or
  deleted files under a guarded root are divergences too.
- **History redirect**: runners pass
  `"history_db_path": temp_history_db(STORE)` in the mem0 config. Without it
  mem0 v2.2.1 defaults its history DB to `~/.mem0/history.db` and BOTH writes
  every ingested session into it AND feeds the last 10 messages of the same
  scope into every extraction prompt ("## Last k Messages" section). All
  runs before 2026-10-25 ran with that live contamination — the discovery and
  its implications are disclosed in the commit history; the redirect moves the
  channel into the per-run temp store, and the guard proves the live dirs
  stay untouched.
- **Self-test** (no stand needed):
  `python3 evals/isolation_guard.py selftest` — writes a probe file into
  `~/.mem0`, expects RED, removes it, expects GREEN again; exit 0 iff both hold.
- Known limitation (honest): a NON-eval process legitimately writing a live
  store while a run is in progress also turns the guard RED; the divergence
  report names the paths so a human can adjudicate.

## 7. Stand verification order

```bash
# 1) the static gate needs no stand at all:
python3 schemas/maqs_way_audit.py all          # expect: GATE GREEN

# 2) smoke (5 stratified questions, ~5–10 min):
python3 evals/pilot_longmemeval_n5.py
# expect: 5 lines [n/5] + 'SMOKE VERDICT: evidence-R@5 (n=5) = 1.00 (stand OK)'
# + '[H5 isolation guard] GREEN — live stores untouched.' (§6);
# evidence 5/5 on a working stand is a meaningful signal; the token-proxy next
# to it is secondary diagnostics, NOT a metric (may read 0/5, see sec 0); the
# artifact is written under a timestamped name and clobbers nothing

# 3) the full run (the g1 reference configuration — grammar baseline):
python3 evals/run_single156_g1.py              # ~1 hour, checkpoint per question
```

Results land in `evals/results/` (JSON with provenance: model, server, seed,
date). The historical runners (`*_oldcfg/fixcfg/b6/b4/ii`) correspond to the
pre-registered packages `evals/prereg-*.md` — run them only together with
their prereg.

## 8. What is NOT part of this recipe

- The posthoc verbatim-metric analysis (`verbatim_*.py`) reads live Qdrant
  stores from `/tmp` — those are ephemeral; after a full run the store lives
  until the next reboot.
- The B6-branch runs require the same preregs and sanctions the author used —
  what is reproducible is the numbers, not the decision process.

## 9. Reporting a reproduction attempt

An independent reproduction is the real test of this recipe, so a report
is useful whether it succeeds or not.

1. **Build the stand from this file only.** Please do not ask the author
   for help along the way: every point where you had to ask would be a
   gap in the recipe.
2. **Log every point where you had to guess**, look something up
   elsewhere, or deviate from the instructions (other OS, GPU, server,
   model build, port). These notes are the most valuable part of the report.
3. **Attach**:
   - the `SMOKE VERDICT` line from `python3 evals/pilot_longmemeval_n5.py`;
   - the output of `python3 schemas/maqs_way_audit.py all`;
   - `pip freeze` from the environment you ran in;
   - OS, GPU and VRAM, llama.cpp build, model file md5.
4. **Open an issue** titled `Reproduction report: <your setup>`.
   Failed or partial attempts are welcome: they are recorded the same way
   as successful ones, never rewritten silently.

A smoke result of `evidence-R@5 = 1.00` means the stand works. A lower
value is not automatically a failure. Report it as-is, together with
your deviation log.
