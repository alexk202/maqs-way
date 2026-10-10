# MAQS-Way — Proposals & Roadmap (beyond v0.1)

> Historical note (v0.1.3): this doc is a v0.1 roadmap snapshot. Canon for thresholds, lifecycle and `visible_to` is `SPEC.md` v0.1.3 + `maqs-way-standard.json` v0.1.3 (`verification_suite.metrics`, `lifecycle.temporal_priority_algorithm`).

**By:** Aleksandr Kossarev   
**Context:** MAQS v1.6 is audit core. MAQS-Way v0.1 is path layer.

---

## Proposal 1: Keep the separation strict

Do not merge Way into MAQS. 

- **MAQS** = `docs/STANDARD.md` — checklist you put on table, item backed by real incident, CRIT/IMP/REC verdict. Polishing only in v1.7 (An 93, 11 sections, example item, I7 reclassified).
- **Way** = `docs/MAQS-WAY-*.md` + `maqs-way-standard.json` — contract for portability, lifecycle, measurable verification. References MAQS sections as implementation evidence.

Reason: OMPS/AMSP/OAMP failed when they tried to be storage engine + protocol + governance at once. MAQS succeeded because it stayed as audit. Keep that.

## Proposal 2: Three concrete deliverables for v0.2

### A. `standard.json` machine-readable (DONE as draft)

File: `maqs-way-standard.json` — already created. Contains:
- 8 principles with property / verification / example separated (fixes way.md critique about mixing)
- Data model ref to OMPS `memory-item.schema.json`
- Lifecycle state machine + bitemporal + 6-tier deletion cascade from tombstone spec
- Verification suite: golden sets LoCoMo/LongMemEval/MemoryAgentBench, metrics R@5≥0.8, temporal≥0.75, abstention≥0.9, duplicate≤0.02, contamination=0, residue=0, negative scenarios
- Logging: EU AI Act Art12 required fields + OTel mapping
- Profiles: Personal / Enterprise / Ephemeral

This enables `maqs audit CLI` — validator drives schemas, not re-encodes rules (like OMPS does).

### B. Conformance vectors (valid/invalid)

Create `conformance/` with language-neutral test vectors [v0.1.3 note: actual layout `conformance/{valid,invalid}/`, no `vectors/` subdir]:

- `valid/001-minimal-preference.omps.json` — minimal portable preference
- `valid/002-bitemporal-fact.json` — fact with valid_at/invalid_at + t_created/t_expired (Graphiti style)
- `valid/003-deletion-tombstone.json` — deletion_log signed, zero PII
- `invalid/001-no-agent-id.json` — missing OAMP binding → must FAIL
- `invalid/002-model-output-as-trusted.json` — model_output without typing → FAIL F7
- `invalid/003-cross-tenant-search.json` — retrieval returns other tenant → FAIL G
- `invalid/004-native-delete-residue.json` — native vector delete leaving 92% residue → FAIL P5 (needs tombstone compaction)

Each vector → manifest.json: expected verdict + rule_ids (P1-P8).

### C. D9 expanded to behavioral test

Closest point where mechanism meets result.

Implement `evals/maqs-way-golden/`:

- 20 queries from LoCoMo single-hop (retrieval)
- 20 from LongMemEval knowledge_updates + abstention
- 10 adversarial: prompt injection via memory (ASI06-001), privilege elevation via summary (ASI06-002), feedback contamination (MAQS F), stale_overrides_fresh
- 10 deletion: logical search, physical scan, semantic similarity, extraction probe

Run harness: `python evals/run_way_evals.py --standard maqs-way-standard.json`

## Proposal 3: Positioning vs existing specs

Do not compete, compose:

- **OMPS** is portability format → Way adopts its `memory-item.schema.json` and `memory-bundle.schema.json` as canonical structural contract.
- **AMSP** is lifecycle + scope model → Way adopts its scope enum and operation set `create/read/search/update/contest/expire/delete/export/import`.
- **OAMP** is provenance enforcement → Way adopts its §4.3 binding and provenance fields `agent_id, session_id, policy_id, source_hash`.
- **Tombstone** is deletion verification → Way adopts its 6-tier cascade and verification lattice as P5 verification.
- **MAQS** is audit → Way references MAQS sections 0-J as evidence that implementation satisfies property.

Diagram:

```
EU AI Act Art12 (what to log)
    ↑
OTel GenAI (how to trace) → Way Logging
    ↑
OMPS/AMSP/OAMP (data model + lifecycle) → Way Architecture
    ↑
MemoryOps / Zep / Mem0 (reference implementations)
    ↑
MAQS v1.6 (how to verify it doesn't break) → Way Verification
```

## Proposal 4: Governance & contribution

- License: Apache-2.0 for spec + MIT for reference code (same as OMPS/AMSP)
- Repo structure:
  ```
  docs/STANDARD.md (MAQS v1.6)
  docs/MAQS-WAY-0.1.md (RU + EN)
  maqs-way-standard.json
  schemas/ (symlink to OMPS schemas + way extensions)
  conformance/vectors/{valid,invalid}/ + manifest.json
  evals/maqs-way-golden/
  ```
- Open questions for v0.2 (explicitly marked, not hand-waved):
  - Conflict resolution: last-write-wins vs explicit contest flow?
  - Forgetting guarantees across replicas: eventual consistency window?
  - Identity continuity across providers: how to verify agent_id signature chain?
  - Multi-agent co-ownership of memory?

## Proposal 5: Immediate next steps (2 weeks)

1. **Freeze Way v0.1 EN** as `docs/MAQS-WAY-0.1-EN.md` — done
2. **Publish `maqs-way-standard.json` draft** — done
3. **Create 7 conformance vectors** (1 day) — I can generate them now [v0.1.3 note: count corrected 8→7, listed items are 3 valid + 4 invalid]
4. **Run tombstone bench on your current stack** — verify 92-100% residue issue exists in your pgvector/Qdrant
5. **Open issue in sanej/amsp and rdh073/omps**: "Propose MAQS as verification layer for AMSP/OMPS contracts" — attach Way v0.1 and mapping table

This keeps MAQS precise in its niche and fills the empty middle you diagnosed as `way.md`.

> Check not that the mechanism exists. Check that it works.

---
