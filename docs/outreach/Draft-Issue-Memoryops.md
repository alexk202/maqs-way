# Draft Issue for patibandlavenkatamanideep/memoryops-ai

**Title:** Proposal: Compose MemoryOps 10 invariants with MAQS-Way measurable verification & tombstone lattice

**Body:**

Hi,

Huge respect for MemoryOps AI — you are one of the few who treat memory not as a vector DB, but as **governed state** with a full lifecycle.

We audited your invariants and they map 1:1 to what we are standardizing in **MAQS-Way v0.1.3**:

Your 10 invariants:
1. Tenant isolation — User A's memory never returned to User B
2. Deletion guarantee — Deleted memories never retrieved
3. Provenance — Every memory traces back to source message/doc
4. Graceful degradation — Retrieval failure never blocks response
5. Policy-before-storage — Unsafe/secret filtered before store
6. Temporary chat — Temporary sessions never write/retrieve
7. Auditability — Append-only audit log for every lifecycle event
8. Explainability — Show which memories affected response
9. Typed memory — Episodic, semantic, procedural, project, knowledge, system
10. Evaluation — Memory quality testable through golden set

**Where MAQS-Way can extend MemoryOps:**

1. **Deletion guarantee — from logical to physical**
You have `deletion compaction` (clears content/embedding, preserves governance tombstone). Tombstone spec `poojan6216/tombstone` shows native `vectorstore.delete()` leaves 92-100% physically recoverable (Chroma 99.8%, Qdrant 100%, pgvector 94.9%). Bench: `DELETE+REINDEX+VACUUM FULL` pgvector, rebuild survivors Qdrant, zero HNSW slots Chroma → 0% residue.

MAQS-Way P5 verification lattice:
- LOGICAL: search() returns 0
- PHYSICAL: file scan 0 residue
- SEMANTIC: Ghost Echoes similarity <0.3, MIA fails
- MODEL: extraction probe fails
Each level Ed25519-signed receipt.

This directly strengthens your invariant #2 and GDPR Art17 compliance.

2. **Bitemporal model from Graphiti**
You have decay, reflection, conflict resolver. Graphiti adds `valid_at/invalid_at` (when event happened) + `t'_created/t'_expired` (when we learned). Useful for your `retention {ttl}` and conflict resolution — e.g., "deadline moved" supersedes with both timelines preserved.

We adopted this in Way lifecycle: `ACTIVE→STALE→CONTESTED→SUPERSEDED→EXPIRED→ARCHIVED→DELETED→TOMBSTONE`

3. **Evaluation — from golden set to measurable R@k**
You have eval harness scaffolding. Way adds concrete metrics from LoCoMo/LongMemEval/MemoryAgentBench:
- R@5 ≥0.7 / ≥0.85 on LongMemEval oracle, temporal accuracy ≥0.65 / ≥0.8, abstention rate ≥0.8 / ≥0.9 when no evidence, duplicate rate ≤5% / ≤2%, contamination rate ≤1% / 0 (CI gate / target)
- Negative scenarios: cross_tenant_leak, prompt_injection_via_memory (OWASP ASI06-001), feedback_contamination (MAQS F), stale_overrides_fresh, shared_fact_visibility_leak

4. **Logging — EU AI Act Art12**
You have append-only audit log. Way adds Art12 required fields: period of use, reference DB checked, input leading to match, natural persons, agent_id, policy_version, outcome, timestamp, ed25519 signature + OTel `gen_ai.conversation.id` mapping. Retention 12 months default, 6 years regulated, WORM lock.

**Proposal:**

- Keep MemoryOps as reference implementation of governed memory.
- Use `maqs-way-standard.json` (8 principles P1-P8 with property/verification/example separated) as machine-readable spec for your invariant evidence gate in CI.
- Add our 7 conformance vectors (valid/invalid) to your `evals/` — especially `invalid-004-native-delete-residue` that fails if physical purge not verified.

Artifacts ready:
- `MAQS-Way v0.1.3 EN` spec (full scan OMPS/AMSP/OAMP/Mem0/Zep/Tombstone/Eval/OWASP/OTel)
- `maqs-way-standard.json`
- `conformance/manifest.json`

Would you accept a PR adding `docs/composition-with-maqs-way.md` showing how your 10 invariants satisfy Way P1-P8 and how tombstone lattice strengthens deletion guarantee?

Thanks for building governance-first memory,

Aleksandr Kossarev
MAQS / MAQS-Way
GitHub: patibandlavenkatamanideep/memoryops-ai is original, lguzzon-scratchbook is fork — posting here in original.
