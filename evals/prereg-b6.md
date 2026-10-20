# Pre-registration: B6 verbatim-preservation fix (single-156 slice)

Written and committed BEFORE the run. Status: `signed` below = owner sanction.
Run: `python3 evals/run_single156_b6.py` (from canon root, mem0-pilot-venv).

## What
Fix ② for the B6 summarization defect (taxonomy per prereg-v03.md:83 — facts
extracted, title lost in paraphrase). Mechanism: mem0 `add(prompt=...)` injects
`evals/b6_prompt.py::B6_VERBATIM` as Custom Instructions into the additive
extraction prompt (verified in mem0@0724291b source: `_add_to_vector_store`
→ `custom_instructions`). Config otherwise identical to (b2)
`run_single156_fixcfg.py`: max_tokens=2000 (fix ① carried), same model/server/
embedder/dataset/selection/committed order. The ONLY eval delta vs (b2) is the
B6 prompt. Generic instruction text, no eval-item-specific examples.

## Predictions (pre-committed, agent's own, per house convention)
- B6-class misses (title lost in paraphrase): **0** (from ≥1 in b2 full-500 taxonomy).
- evidence-R@5: within noise of b2 0.987; predict [0.980, 0.995]. Guard: not below 0.970.
- malformed_class parse failures: unchanged ~1.3% (prompt does not touch truncation).
- finish_reason length share: unchanged ~1.3%, hard guard ≤ 2.6% (b1 level).
- empty collections: ≤ b2 level (4/156).

## Decision rule
- B6-class = 0 AND R@5 ≥ 0.980 AND guards hold → fix CONFIRMED on slice;
  promote same prompt to the full-500 harness (pre-committed here: the full-500
  B6 run will pass the identical `B6_VERBATIM`, no wording changes).
- B6-class > 0 → inspect residues item-by-item; no silent rollover, no rule
  rewriting after numbers.
- Any guard violated → fix REJECTED on slice, residue analysis before retry.

## Prerequisites (lessons 17.10)
- :8085 llama-server up (key /tmp/opencode/pilot8085.key); :1449 nomic embedder
  up (lms load if unloaded). :8080/:8083 — owner's, do not touch.
- Fresh store dir per run (script self-stamps). Checkpoint per question.
- After run: delete `evals/__pycache__`, `git status` shows only intended files.

## Signature
- [x] owner sanction: Aleksandr Kossarev, 2026-10-20 (chat command «Коммит») — package committed same day, before any run.
