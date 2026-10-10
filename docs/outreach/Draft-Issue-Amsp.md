# Draft Issue for sanej/amsp — Proposal: MAQS as Verification Layer for AMSP

**Title:** Proposal: Use MAQS-Way as verification / conformance layer for AMSP contracts

**Body:**

Hi Sanej,

Thanks for AMSP v0.1 — the clearest articulation I've seen that MCP = tool access, A2A = agent-to-agent, and **memory persistence still lacks an open governance contract**.

We are working on a complementary layer: **MAQS-Way** — the path from policies to implementation.

**Context:**
- **MAQS v1.6** (Memory Architecture Quality Standard) is a practical audit checklist derived from 20k+ tracebacks and production incidents across multi-layer memory systems (self-contamination loops, non-deterministic keys, secret leakage, volume doubling, embedding mismatch, etc.). Each item is backed by a real incident. It covers: Map, Input validation, Write integrity, Growth, Retrieval, Assembly, Feedback loop, Isolation, Concurrency, Observability, Change Management.

- **way.md external review** of MAQS identified the gap: checklist proves mechanism exists (relevance threshold, dedup), but does not prove memory *actually* recalls needed, forgets outdated, and doesn't contaminate. Suggested three layers: Principles / Architecture / Verification.

- **MAQS-Way v0.1.3** implements those three layers and is intentionally complementary to AMSP/OMPS/OAMP.

**Why this fits AMSP:**

AMSP defines:
- object schema, lifecycle `active, stale, expired, contested, superseded, deleted`
- scope model `local-session, agent-private, user-private, user-portable, team-shared, org-shared, public-reference` (Way canon uses the 5-value subset without `user-private`/`public-reference`)
- ops `create/read/search/update/contest/expire/delete/export/import`
- governance: permissions, provenance, retention, audit

MAQS-Way adds what AMSP lists as open questions:
- **Measurable quality**: golden sets LoCoMo / LongMemEval / MemoryAgentBench with metrics as CI gate / target pairs (R@5 ≥0.7 / ≥0.85, temporal ≥0.65 / ≥0.8, abstention ≥0.8 / ≥0.9, duplicate ≤5% / ≤2%, contamination ≤1% / 0)
- **Deletion verification lattice**: LOGICAL / PHYSICAL / SEMANTIC / MODEL with tombstone compaction (bench: native delete leaves 92-100% recoverable in Chroma/Qdrant/pgvector)
- **Security**: OWASP Agentic Top10 ASI06 Memory Poisoning tests ASI06-001/002
- **Observability**: EU AI Act Art12 + OTel GenAI `gen_ai.conversation.id` mapping

**Proposal:**

1. Keep AMSP as canonical schema + lifecycle + scope contract.
2. Use MAQS-Way `maqs-way-standard.json` + `conformance/vectors/` as verification corpus for AMSP implementations.
3. Map: AMSP scope model → MAQS G Isolation negative tests; AMSP lifecycle → MAQS B/C + tombstone cascade; AMSP export/import → MAQS-Way portability profile.

We have draft artifacts:
- `MAQS-Way v0.1.3 EN` spec
- `maqs-way-standard.json` machine-readable (8 principles P1-P8 with property/verification/example separated)
- 7 conformance vectors valid/invalid + manifest.json

Would you be open to a PR that adds a `docs/verification-with-maqs.md` referencing MAQS as optional verification layer? Or we could co-author a short RFC: "AMSP + MAQS-Way composition".

Happy to align on license (Apache-2.0 for spec, MIT for code like OMPS).

Best,
Aleksandr Kossarev
MAQS / MAQS-Way
Links: [spec draft], [standard.json], [conformance]

---
*This draft is prepared for GitHub issue submission.*
