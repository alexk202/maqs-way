# Draft Issue for rdh073/omps — Proposal: MAQS-Way verification + tombstone lattice for OMPS

**Title:** Proposal: Compose OMPS portability with MAQS-Way measurable verification & deletion lattice

**Body:**

Hi,

Great work on OMPS v0.1 — `memory-item.schema.json`, `memory-bundle.schema.json`, `deletion-marker.schema.json` with `consent {exportable, usable_for_training}`, `retention {until_deleted}`, `provenance {created_by, source, confidence}` plus validator and conformance vectors is exactly the vendor-neutral portability layer the ecosystem needed.

We are building a complementary layer that directly uses OMPS schemas: **MAQS-Way**.

**What is MAQS:**
- MAQS v1.6 is an audit checklist (Map, Input validation, Write integrity, Growth, Retrieval, Assembly, Feedback contamination, Isolation, Concurrency, Observability, Change Management) where each CRIT item is backed by a production incident (20k tracebacks, secret leakage, volume doubling, embedding mismatch).
- External review `way.md` pointed out: checklist proves mechanism exists, but not that memory actually works. Suggested three layers: Principles / Architecture / Verification.

**What is MAQS-Way v0.2:**
- **Principles**: 8 immutable (Veracity, Provenance, Controlled Aging, Isolation, Deletability, Recoverability, Portability, Measurability)
- **Architecture**: adopts OMPS `memory-item` as base, extends with OAMP §4.3 `agent_id` binding mandatory, bitemporal `valid_at/invalid_at + t_created/t_expired` from Graphiti, 6-tier deletion cascade `graph_edges → nodes_if_sole_provenance → embeddings_fk → facts_fk → artifacts → rounds` from tombstone spec
- **Verification**: This is where OMPS could benefit:
  - Your conformance corpus validates structure. MAQS-Way adds behavioral verification: LoCoMo / LongMemEval / MemoryAgentBench golden sets (CI gate / target: R@5 ≥0.7 / ≥0.85, temporal ≥0.65 / ≥0.8, abstention ≥0.8 / ≥0.9)
  - Deletion lattice from `poojan6216/tombstone`: LOGICAL (search returns 0), PHYSICAL (DELETE+REINDEX+VACUUM / rebuild survivors, 0 residue — bench shows native delete leaves 92-100% recoverable), SEMANTIC (Ghost Echoes, MIA fails), MODEL (extraction probe fails), each Ed25519-signed
  - Security: OWASP ASI06-001 false-fact injection, ASI06-002 privilege elevation via summary

**Composition proposal:**

```
OMPS schemas (structural contract) ← MAQS-Way adopts as canonical
  ↓
AMSP scope + lifecycle (governance contract)
  ↓
MAQS-Way standard.json + vectors (behavioral + deletion verification)
  ↓
MAQS v1.6 (incident-backed audit as evidence)
```

Concretely:
- OMPS remains source of truth for `memory-item.schema.json` and `memory-bundle.schema.json`
- MAQS-Way `maqs-way-standard.json` references OMPS schemas via `$ref` and adds `property/verification/example` separation (fixes way.md critique)
- Conformance: OMPS `valid/invalid` vectors + MAQS-Way vectors `invalid-001-no-agent-id`, `invalid-002-model-output-as-trusted` (F7), `invalid-003-cross-tenant`, `invalid-004-native-delete-residue` can be merged into one manifest

**Artifacts ready:**
- `MAQS-Way v0.2 EN` (full scan of OMPS/AMSP/OAMP/Mem0/Zep/Tombstone/Eval/OWASP/OTel)
- `maqs-way-standard.json`
- `conformance/manifest.json` with 12 vectors

**Ask:**
Would you accept a PR that:
- adds `docs/composition-with-maqs-way.md` explaining OMPS + MAQS-Way composition
- adds `examples/maqs-way/` with bitemporal fact example using `valid_at` + `t_created`
- references MAQS-Way deletion lattice in your `deletion-marker.schema.json` docs

We keep OMPS as structural contract, MAQS-Way as verification layer — two docs, one coordinate system.

Thanks for opening this space,
Aleksandr Kossarev
MAQS / MAQS-Way

---
*Draft for GitHub issue*
