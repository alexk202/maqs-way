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
Thresholds: first real runs happened October 2026 (LongMemEval single-156 pilots:
b1/b2, stratified-50, grammar baseline g1, package-(ii)); measured baselines live
in `results/` with provenance, and guard thresholds are pre-registered per run in
`prereg-*.md`. The table above stays the target ladder; per-run guards are set by
the run's prereg, not by this table.

## Reproducing the runs

See **[REPRODUCE.md](REPRODUCE.md)** (EN, canonical; [RU mirror](REPRODUCE-RU.md)) — full stand recipe: pinned
`requirements.txt` (mem0 at an exact upstream commit), the LLM/embedder servers,
checksums, env overrides (`eval_config.py`), smoke mode, timing/VRAM, and the
honest GPU-nondeterminism caveat (compare in bands, not third decimals).

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

Isolation (MAQS H5 [CRIT]): evals run on temp/in-memory stores with mocked APIs, never on live memory; guard check before/after live directories confirms no artifacts leaked.
