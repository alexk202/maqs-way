# Landscape scan Oct 2026

Full scan done 2026-10-10. Live verification 2026-10-10 — legend: ✅ confirmed live, ⏳ wording from secondary sources:

- OMPS rdh073/omps v0.1 — memory-item.schema.json, deletion-marker.schema.json, consent, retention, provenance, validator + conformance vectors — verified: ✅
- AMSP sanej/amsp v0.1 — lifecycle active/stale/expired/contested/superseded/deleted, scope local-session/.../public-reference, ops create/read/search/update/contest/expire/delete/export/import — verified: ✅
- OAMP deep-thinking-lab v1.2/1.3 — agent_id, session_id, timestamp, policy_id, source_hash, valid_from/valid_to, deletion_event signature chain, binding entry.source.agent_id == oamp_agent_id — verified: ✅
- MCP Memory Servers @modelcontextprotocol/server-memory — Entity {name, entityType, observations[]}, Relation, flat file per instance — verified: ✅
- MemoryOps AI patibandlavenkatamanideep/memoryops-ai — 10 invariants, Write Path Gateway→Extractor→Policy Broker→Write→Audit, deletion compaction preserves governance tombstone — verified: ✅
- Mem0/Mem0g arXiv:2504.19413 — add() → ADD/UPDATE/DELETE/NOOP, vector store, LoCoMo 66.9%/68.44%, gap provenance-erased — verified: ✅
- Zep/Graphiti getzep/graphiti arXiv:2501.13956 — bitemporal T/T', t'_created/t'_expired, valid_at/invalid_at, invalidation-on-contradiction, Episode→Entity→Community, DMR 94.8%, LongMemEval +18.5%, deletion = invalidated not deleted — verified: ✅
- Tombstone poojan6216/tombstone — 6-tier cascade Rounds→Facts→Artifacts→pgvector→FalkorDB→thinking, verification lattice LOGICAL/PHYSICAL/SEMANTIC/MODEL, bench native delete 92-100% recoverable, tombstone 0% — verified: ✅
- Eval benchmarks LoCoMo (10 dialogs 600 turns), LongMemEval (500 Qs 115K tokens, abstention), MemoryAgentBench ICLR2026 (146 contexts 273K-3.17M, AR/TTL/LRU/CR) — verified: ✅ (LoCoMo figures per Mem0-paper setup; full dataset is 50 dialogues)
- Security OWASP LLM Top10 2025/26 LLM01 Prompt Injection, OWASP Agentic Top10 ASI06 Memory & Context Poisoning, MITRE ATLAS AML.T0080 — verified: ✅
- Observability EU AI Act Art12/13/19 automatic logging, Art19 period of use, reference DB, input leading to match, 6 months retention, OTel GenAI gen_ai.operation.name, conversation.id, tool.name, usage.tokens — verified: ⏳ (OTel semconv confirmed live; Art12 wording per standard knowledge, not letter-checked)
