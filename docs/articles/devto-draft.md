---
title: "MAQS-Way: The Path Layer MAQS Was Missing — From Policies to Measurable Memory"
published: false
tags: ai, llm, memory, architecture, governance, maqs, omps, amsp, oamp
canonical_url: https://github.com/your-account/maqs-way
---

# MAQS-Way: The Path Layer MAQS Was Missing

MAQS (Memory Architecture Quality Standard) became a rare artifact: an audit checklist for long-term memory in LLM assistants, backed by 20k+ tracebacks and production incidents. It tells you **how to verify that memory doesn't break**.

But after external review `way.md` we realized: there's a gap between policies and implementation.

- Policy layer is overcrowded: GDPR Art17, EU AI Act Art12, RBAC — what *should* be.
- Audit layer exists: MAQS — how to ensure it doesn't break.
- Path layer was missing: which schemas, lifecycles, patterns to use and how to prove it works.

That path is **MAQS-Way**.

## What already exists (Oct 2026 scan)

We scanned open field:

- **OMPS** `rdh073/omps` — vendor-neutral portability `memory-item.schema.json`, `deletion-marker.schema.json`
- **AMSP** `sanej/amsp` — schema + lifecycle `active→deleted` + scope `user-portable` etc
- **OAMP** `deep-thinking-lab` — provenance mandatory `agent_id` binding §4.3
- **Zep/Graphiti** `getzep/graphiti` — bitemporal `valid_at/invalid_at + t_created/t_expired`, invalidation-on-contradiction, DMR 94.8%
- **MemoryOps AI** `patibandlavenkatamanideep/memoryops-ai` — 10 invariants, Write Path Gateway→Extractor→Policy Broker→Write→Audit
- **Tombstone spec** — 6-tier deletion cascade, bench: native vector delete leaves 92-100% recoverable, tombstone 0%
- **LoCoMo/LongMemEval/MemoryAgentBench** — measurable R@k, temporal, abstention
- **OWASP Agentic ASI06** — Memory & Context Poisoning
- **EU AI Act Art12 + OTel GenAI** — logging by design

None of them alone is the path. Together they form it.

## MAQS-Way v0.1.3 — Three layers

### 1. Principles (8 immutable)

Veracity, Provenance, Controlled Aging, Isolation, Deletability, Recoverability, Portability, Measurability

### 2. Architecture

- Data model: OMPS base + OAMP mandatory `agent_id`, `provenance append-only`, `admitted≠trusted`
- Lifecycle: `ACTIVE→STALE→CONTESTED→SUPERSEDED→EXPIRED→ARCHIVED→DELETED→TOMBSTONE→COMPACTION` + bitemporal
- Deletion: 6-tier cascade `graph_edges → nodes_if_sole_provenance → embeddings_fk → facts_fk → artifacts → rounds` in one transaction + best-effort graph reconciliation
- Tombstone: `deletion_log(request_id, timestamp, scope, layer_counts, requestor)` zero PII, Ed25519-signed, hash-chained
- Isolation: scope model `local-session < agent-private < user-portable < team-shared < org-shared`, negative tests cross-tenant 0 leak + G1 fixtures (wrong scope, read-only write, after revocation)
- Content-as-Data: fenced `<retrieved_context type=model_output>`, blind truncation prohibited

### 3. Verification — Check not that mechanism exists. Check that it works.

Each item: Property / Verification / Example separated.

Minimal golden set:

| Property | CI gate | Target |
|---|---|---|
| Retrieval | R@5 ≥0.7 LongMemEval oracle | R@5 ≥0.85 |
| Temporal | ≥0.65 | ≥0.8 |
| Abstention | ≥0.8 when no evidence | ≥0.9 |
| Duplicate | ≤5% | ≤2% |
| Contamination | ≤1% | 0 |
| Deletion residue | 0% LOGICAL/PHYSICAL/SEMANTIC/MODEL | 0% |
| Isolation leak | 0 | 0 |
| Poisoning BLOCK | 100% ASI06 | 100% |

Logging: EU AI Act Art12 required fields + OTel `gen_ai.conversation.id` + tamper-evident hash-chain, 12 months default, 6 years regulated, WORM lock.

## Relation to MAQS

- MAQS v1.6 = audit checklist you put on table, CRIT/IMP/REC verdict
- Way = governance contract that references MAQS sections 0-J as implementation evidence

Two repos, one coordinate system.

MAQS: https://github.com/alexk202/memory-architecture-standard
Way: https://github.com/your-account/maqs-way

- maqs-way-standard.json — machine-readable 8 principles P1-P8
- conformance/valid/invalid + manifest.json — 7 vectors (no-agent-id, model-output-as-trusted, cross-tenant, native-delete-residue, deletion-tombstone)
- evals/ — how to run LoCoMo/LongMemEval

## Next

- Freeze Way v0.1.3, publish conformance, run tombstone bench on your stack
- Open issues in OMPS/AMSP/OAMP/MemoryOps/Zep proposing MAQS-Way as verification layer (drafts in docs/outreach/)

Check not that the mechanism exists. Check that it works.

---
*Draft for DevTo, tags: maqs, llm-memory, ai-governance, omps, amsp, oamp, graphiti, memoryops*
