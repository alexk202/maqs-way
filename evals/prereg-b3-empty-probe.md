# Pre-registration: Lock 4 probe — 11 b3-empty questions at b3 config

Status: DRAFT → owner sanction → commit hash → run (~5–10 min). Diagnosis only.
Purpose: answer the council's Lock 4 **before** b4: were the 11 empty questions in b3 limited
by the 2000-token wall (silent truncation: valid-but-empty/partial JSON), or did
extraction validly return empty?

## What
- Questions: exactly the 11 q_ids empty in b3 (committed list in `run_b3_empty_probe.py`).
- Config: b3 EXACTLY — `max_tokens=2000`, `B6_VERBATIM` (sha256 73c485c1…, unchanged),
  same model/embedder/committed order; fresh store per question.
- Instrumentation: per-call `finish_reason / parse / chars`, per-question `memories`.
- No B6 wording change, no cap change, no new prompt. This is a reproduction probe.

## Known before the run (so the probe is interpretable)
- b3 artifacts cannot answer Lock 4: b3 had only global counters, no per-question
  finish_reason/chars. This probe exists precisely to close that instrumentation gap.
- Server-log aggregates for the b3 window: 7 completions at the 2000 wall, 6 short
  (<300 tokens), 0 cancellations; ~141 completions vs 156 questions (wrapper 156) —
  per-question attribution impossible without this probe.
- Dataset statics: all 11 empty questions have normal sessions (2–20 msgs, 2–19k chars),
  so "empty session ⇒ no LLM call" is excluded.

## Interpretation (hard-coded before numbers)
- **If any of the 11 shows `finish_reason=length` or chars near the cap (≥ ~7000) on a
  call that yielded 0 memories** → silent truncation channel CONFIRMED for b3 empties
  (valid-but-empty after salvage). b4 (cap 4000) becomes the decisive test of the
  delivery hypothesis; grammar-layer plan keeps its separate length guard.
- **If all 11 reproduce empty with `stop` and short outputs** → "valid empty extraction"
  CONFIRMED; B6 prompt behavior is the mechanism; variant 4 (narrow verbatim) is the
  mandatory next step (per the council's branch-1 reformulation in prereg-b4 §3).
- **If empties do NOT reproduce** (any q returns memories>0) → nondeterminism/batch
  dependence is real; record it, b4 remains necessary, and no fix claims are made.
- Mixed outcome → report per-question table; no aggregated hand-waving.

## Discipline
- Launch only `setsid nohup ... < /dev/null > log 2>&1 &`, no waits in the launch command.
- Servers :8085/:1449 up first; after run, copy log + server-recount into `evals/results/`.
- After run: `evals/__pycache__` removed, `git status` clean.
- Then: append the required line «finish_reason/длина у 11: …» to `prereg-b4.md` (до чисел
  b4), после чего b4 подписывается.

## Signatures
- [x] owner sanction: Aleksandr Kossarev, 2026-10-20 (chat: «Делай коммит»)
- [x] commit hash пакета: `c726775`; прогон отложен на 2026-10-21 (до/вместе с b4)
