# Paired per-question comparisons under confirmed byte-identity (v0.1, NOT canon)

> Status: formulation proposal to the owner, 2026-10-25. NOT normative, NOT
> applied: the branch canon «per-question intersections are NOT interpreted»
> stays operative in evals/ (REPRODUCE.md §0, line 3; preregs of the b/g1
> line) until owner canonization with signature. Preregs of past packages
> are not affected by this document.

## Current rule (branch canon, Oct 2026)

Per-question intersections between runs are NOT interpreted; numbers are
compared in bands and class compositions. Origin: the b3-empty-probe era —
9/11 empty questions did not reproduce between runs and the divergence was
attributed, at the time, to GPU nondeterminism (annotated 2026-10-25: the
probable cause was shared history tails, i.e. different prompts —
`evals/results/g1iso_attractors_note.md`).

## Proposed replacement (isolated runs, same stand only)

For runs under **per-question history isolation** (the post-`ffb5879` runner
family) on the **same reference stand** (same GPU/driver/llama.cpp build),
paired per-question comparisons ARE admissible when a control panel's
byte-identity is confirmed in the same time window:

1. Alongside the compared runs, execute a control panel under the same
   config; standing candidates: the frozen 12-id verbatim pair-panel
   (stable questions) and `run_g1iso_attractors.py` (the stricter set —
   includes the metastable attractor questions).
2. The control must come out **byte-identical within the window** (raw
   extraction outputs; the current tooling already dumps them).
3. Then per-question differences between the isolated runs are attributable
   to the runs' controlled deltas (config/prompt), and paired per-question
   interpretation is admissible.
4. If the control panel diverges, the bands rule applies unchanged.

## Boundary (why scoped)

- **Same stand only**: cross-stand determinism (other GPU/driver/build) is
  untested — REPRODUCE.md §0 (2026-10-25 formulation): compare externally
  in bands.
- **Isolated runs only**: any run still carrying a history-tail channel has
  prompt variance by construction — the tail shifted fact vectors at
  ~135/156 questions (`evals/results/history_confound_forensics.md`,
  `g1iso_attractors_crosscheck.json` three-way analysis).
- **Evidence basis**: `results/g1iso_determinism_check.json` (panel-12,
  within and across restarts), `results/g1iso_attractors_crosscheck.json`
  (attractor questions, three server instances).

## Effect if canonized

Unlocks paired per-question analysis for isolated same-stand comparisons
(e.g., the (ii)-line verbatim per-member deltas, worst-20 paired analysis,
per-question regression attribution) without re-running N-repeat bands for
every question — the control panel carries the determinism burden once per
window instead. All past preregs keep their wording; future preregs would
cite this rule in their decision sections.
