# Evals — How to run measurable verification

## Golden sets

- LoCoMo: 10 multi-session dialogs avg 600 turns, categories single-hop/multi-hop/temporal/open-domain/adversarial
- LongMemEval: 500 questions 115K tokens, abilities extraction/multi-session reasoning/temporal/knowledge updates/abstention, metrics R@1/5/10, NDCG, MRR
- MemoryAgentBench: 146 long contexts 273K-3.17M, competencies AR/TTL/LRU/CR, FactConsolidation

## Minimal suite for Way

| Property | Test | CI gate | Target |
|---|---|---|---|
| Retrieval | LoCoMo single-hop; LongMemEval oracle | R@5 ≥0.7 | R@5 ≥0.85 |
| Knowledge update | LongMemEval updates | — | ≥0.7 |
| Temporal | LoCoMo temporal | ≥0.65 | ≥0.8 |
| Abstention | LongMemEval abstention | ≥0.8 | ≥0.9 |
| Deduplication | Duplicate injection | ≤5% | ≤2% |
| Contamination | Feedback loop probe | ≤1% | 0 |
| Deletion | Tombstone cascade | 0% residue | 0% |
| Shared-fact masking | After delete of shared fact | 0 leak | 0 |
| Isolation | cross-tenant | 0 leak | 0 |
| Poisoning | ASI06-001/002 | BLOCK 100% | BLOCK 100% |

Canon: `maqs-way-standard.json` → `verification_suite.metrics`.

**Headline (owner rule, 2026-10-26): full-500-iso evidence-R@5 = 0.988**
(494/500, Wilson [0.974, 0.994]) — the first ISOLATED full-500 (per-question
history isolation, H5 guard, `prereg-full500-iso.md`; artifacts in `results/`).
The pre-isolation full-500 of Oct-17 (0.992) stays in history with the confound
annotation (`results/full500iso_verdicts.md`,
`results/history_confound_disclosure_note.md`).
Thresholds: first real runs happened October 2026 (LongMemEval single-156 pilots:
b1/b2, stratified-50, grammar baseline g1, package-(ii)); measured baselines live
in `results/` with provenance, and guard thresholds are pre-registered per run in
`prereg-*.md`. The table above stays the target ladder; per-run guards are set by
the run's prereg, not by this table.

## Reproducing the runs

See **[REPRODUCE.md](REPRODUCE.md)** (EN, canonical; [RU mirror](REPRODUCE-RU.md)) — full stand recipe: pinned
`requirements.txt` (mem0 at an exact upstream commit), the LLM/embedder servers,
checksums, env overrides (`eval_config.py`), smoke mode, timing/VRAM, and the
honest determinism boundary measured 2026-10-25 (reference-stand byte-identity,
attractor questions included; earlier irreproducibility was history tails, not
GPU; external comparisons in bands — sec 0).

Quick start on a working stand:

```bash
python3 schemas/maqs_way_audit.py all      # static gate, no stand needed
python3 evals/pilot_longmemeval_n5.py      # smoke: 5 questions, ~5-10 min
python3 evals/run_single156_g1.py          # reference run: single-156, ~1 h
```

Runners (`run_single156_*.py`, probes) are pre-registered experiment packages:
each corresponds to a signed `prereg-*.md` with pre-committed guards and
predictions — read the prereg before re-running, and never compare numbers
across different packages without their preregs.

Isolation (MAQS H5 [CRIT]): every runner wraps `main()` in `@guarded()` from
`evals/isolation_guard.py` — live roots (`~/.mem0`, qdrant defaults) are snapshotted
before the run and verified after; divergence → RED + non-zero exit. The mem0
history DB is redirected PER QUESTION into the temp store
(`temp_history_db(f"{STORE}/q{qi}")`; mem0 v2.2.1 otherwise reads/writes the live
`~/.mem0/history.db`, feeding a last-10-messages tail into the extraction prompt;
the earlier per-run granularity kept the within-run tail — superseded 2026-10-25,
see `results/g1iso_a_note.md`). SQLite compared by logical rows, never md5 (WAL
checkpoint trap). The guard runs in EVERY run, built into the runner — details
in REPRODUCE.md §6.

**mem0-native run_id isolation (measured 2026-10-26 by the P4 demo,
not adopted yet)**: giving each `add()` a distinct `run_id` natively isolates
the per-question history tail in mem0@0724291b (the messages/history scope is
keyed by the sorted `user_id&run_id` pair — the q2 scope holds only its own
rows). A candidate alternative/complement to the per-question history DB; the
H5 guard stays regardless (it guards the live roots). See
`results/p4_mem0_isolation_report.json` (incident demo) and REPRODUCE.md §6.
