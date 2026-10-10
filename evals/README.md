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

Canon: `maqs-way-standard.json` → `verification_suite.metrics`. Thresholds indicative until first real run.

Planned harness interface (v0.2, see SPEC §6 Backlog; script not yet shipped):

```bash
python evals/run_way_evals.py --standard maqs-way-standard.json
```

Isolation (MAQS H5 [CRIT]): evals run on temp/in-memory stores with mocked APIs, never on live memory; guard check before/after live directories confirms no artifacts leaked.
