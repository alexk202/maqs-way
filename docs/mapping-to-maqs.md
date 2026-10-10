# Mapping MAQS v1.6 → MAQS-Way v0.1.4

| MAQS Section | Typical failure | Way property | Verification |
|---|---|---|---|
| 0 Map | hidden store, orphaned vectors | P2 Provenance | schema validation OAMP §4.3 |
| A Input validation | secret leakage to memory | P1 Veracity Content-as-Data | OWASP ASI06 BLOCK 100% |
| B Write integrity | non-idempotent indexing, volume doubling | P5 Deletability + P2 | tombstone cascade + provenance append |
| C Growth | unbounded growth, loss on restart | P3 Controlled Aging | bitemporal valid_at + decay |
| D Retrieval | old displaces new, empty context | P8 Measurability | R@5 ≥0.7/≥0.85, temporal ≥0.65/≥0.8, LoCoMo |
| E Assembly | blind truncation mid-word | P1 + P3 | budget + fenced context |
| F Feedback | model analyzes own reports, self-contamination | P1 | model_output typed, contamination ≤1% / 0 |
| G Isolation | traces of unrelated topics | P4 Isolation | cross-tenant negative 0 leak |
| H Concurrency | database is locked | P6 Recoverability | versioned embeddings fallback |
| I Observability | warnings always existed | Logging | EU AI Act Art12 + OTel |
| J Change Management | simultaneous changes, no regression test | Reporting | golden set + regression guard |

I7 diagnostic self-interrogation → supplementary signal, not evidence (as proposed in way.md).
