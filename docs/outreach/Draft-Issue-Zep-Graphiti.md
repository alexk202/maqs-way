# Draft Issue for getzep/graphiti and getzep/zep

**Title:** Proposal: Graphiti bitemporal model as Way lifecycle + OMPS deletion marker + tombstone verification

**Body:**

Hi Zep team (Daniel, Preston, Pavlo),

Graphiti is the closest to what we are calling **MAQS-Way** — bitemporal knowledge graph with Timeline T (event time) and T' (ingestion time), edge fields `t'_created, t'_expired, valid_at, invalid_at`, invalidation-on-contradiction, and Episode→Entity→Community (Louvain). Paper arXiv:2501.13956 and benchmarks DMR 94.8%, LongMemEval +18.5% with 90% latency cut are impressive.

We are standardizing the missing middle between policies and implementation: **MAQS-Way v0.1.3**.

**What we adopted from Graphiti:**

Way lifecycle is directly inspired by Graphiti:
```
[ingestion] → ACTIVE → STALE → CONTESTED → SUPERSEDED → EXPIRED → ARCHIVED → DELETED → TOMBSTONE
```
with bitemporal:
- `valid_at/invalid_at` = when fact was true
- `t'_created/t'_expired` = when we learned it

This solves the "stale overrides fresh" problem MAQS D catches.

**Where Graphiti could benefit from Way:**

1. **Deletion semantics — from invalidated to verifiable**

Current behavior (docs):
- Default is *invalidated, not deleted*
- `remove_episode()` deletes edges *uniquely sourced* from that episode, or cascade-deletes facts left unsupported

For GDPR Art17 and EU AI Act Art12, regulators require verifiable deletion. Tombstone spec shows native vector delete leaves 92-100% recoverable. Way proposes:

- Use OMPS `deletion-marker.schema.json` on top of `remove_episode()`: `deletion_log(request_id, timestamp, scope, layer_counts, requestor)` zero PII, Ed25519-signed, hash-chained
- Verification lattice: LOGICAL (search returns 0) / PHYSICAL (DELETE+REINDEX+VACUUM FULL pgvector, rebuild survivors Qdrant, zero HNSW slots Chroma) / SEMANTIC (embedding similarity <0.3, MIA fails) / MODEL (extraction probe fails)
- Preserve governance tombstone even after hard compaction — same as MemoryOps does

2. **Scope model from AMSP**

Graphiti has user_id grouping. AMSP scope model `local-session, agent-private, user-private, user-portable, team-shared, org-shared, public-reference` gives formal boundaries (Way canon uses the 5-value subset). Way P4 Isolation verification: negative test cross-tenant retrieval returns 0, including vector path.

3. **Measurable verification**

You have `benchmarks/` LoCoMo, LongMemEval. Way adds:
- Metrics as CI gate / target pairs: R@5 ≥0.7 / ≥0.85 on oracle, temporal accuracy ≥0.65 / ≥0.8, abstention ≥0.8 / ≥0.9
- Security: OWASP Agentic ASI06-001 false-fact injection via memory, ASI06-002 privilege elevation via summary manipulation — Graphiti's citation to source episode is natural defense, but needs BLOCK test

**Composition:**

```
Graphiti (temporal KG engine, bitemporal) → Way Architecture (lifecycle + tombstone)
  ↓
Zep (managed memory) → Way Profiles (Personal / Enterprise with Art12 logging + OTel)
  ↓
MAQS v1.6 (audit of edge failures) → Way Verification (how to prove deletion/isolation works)
```

**Artifacts ready:**
- `MAQS-Way v0.1.3 EN` — full landscape OMPS/AMSP/OAMP/Mem0/Zep/Tombstone/Eval/OWASP/OTel
- `maqs-way-standard.json` — 8 principles P1-P8 with property/verification/example separated, lifecycle with your bitemporal fields
- 7 conformance vectors including `valid-002-bitemporal-fact` using `valid_at + t_created`

**Ask:**

Would you accept a PR/docs contribution that:
- Documents Graphiti bitemporal fields as reference implementation for Way 2.2 lifecycle
- Adds `deletion-marker` example showing how to make `remove_episode()` GDPR-verifiable with tombstone lattice
- Adds mapping table: Graphiti edge fields → OMPS provenance fields → Way P2/P3/P5

Graphiti remains the engine. Way becomes the governance contract that proves it meets deletion and provenance requirements.

Thanks for open-sourcing Graphiti,

Aleksandr Kossarev
MAQS / MAQS-Way
Refs: getzep/graphiti, getzep/zep, arXiv:2501.13956, https://www.getzep.com

---
Post in: https://github.com/getzep/graphiti/issues and https://github.com/getzep/zep/issues
