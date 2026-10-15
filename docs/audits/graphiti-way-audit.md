# Way-audit of Graphiti OSS (MAQS-Way v0.2 application example)

> Status: draft audit example, NOT part of the canon. Tone — help, not a roast.
> Method: static code reading (no execution, no infra).
> Audited code: `getzep/graphiti` @ `aca3693` (2026-10-15), shallow clone.
> Auditor: MAQS-Way v0.2 (principles P1–P8 + write integrity B1–B6).
> Rule: only facts from code/docs, with paths; whatever was not verified is stated as such.

## Summary

| Way property | Verdict | One line |
|---|---|---|
| P3 Aging | PARTIAL (invalidation covered) | Contradiction retains + expires the old edge, never deletes it |
| P4 Isolation | PARTIAL (mechanism covered) | `group_id` partition + pre-top-k filters; unscoped search allowed |
| P1 Veracity | PARTIAL (typed, unscored) | Strict entity/edge typing enforced; no confidence/trust field stored |
| P2 Provenance | PARTIAL | Bitemporal bounds + episode links; no created_by/agent on records |
| P5 Deletability | PARTIAL | Hard `DETACH DELETE`, no tombstone; expired edges double as implicit tombstone |
| B Write integrity | PARTIAL | Strong dedup pipeline (exact+fuzzy+LLM); real transactions Neo4j-only |
| Logging | GAP (audit) / PARTIAL (tracing) | No audit sink; optional OTel, NoOp default |
| P8 Measurability | COVERED | Unit + int + e2e suites, LongMemEval oracle vendored |

## Done well (worth crediting)

1. **Invalidation-on-contradiction (P3).** `edge_operations.py:748-781`
   `resolve_edge_contradictions()` — the old edge is retained with
   `expired_at` set (`727-728, 741-743`), later `valid_at` supersedes earlier.
   This is exactly the bitemporal discipline Way P3 references — deletion of
   history is refused by construction.
2. **Typed extraction (P1-half).** `entity_types/entity_type_map`,
   `ExtractedEntity.entity_type_id`, strict edge types
   (`graphiti.py:1342-1345`, `prompts/extract_nodes.py:29-39`) with Pydantic
   enforcement — model output enters the graph through a typed gate.
3. **Partitioned retrieval (P4-half).** `group_id` on every node/edge
   (`nodes.py:96`, `edges.py:51`); Lucene prefix + Cypher `IN $group_ids`
   applied before vector/fulltext top-k (`search_utils.py:95-111,229`).
4. **Evals shipped (P8).** Unit, integration (dockerized), e2e graph-building
   plus LongMemEval oracle under `tests/evals/` — the fullest verification
   story among audited systems so far.

## Gaps with specifics (what to improve, per file)

1. **P4 — unscoped search allowed.** `search(group_ids=None)` is permitted
   (`helpers.py:171-178`, `graphiti.py:1907`): the mechanism is correct, but
   enforcement is opt-in. Suggestion: require explicit scope or an
   `unscoped=True` acknowledgment flag (fail-closed by default).
2. **P1 — no confidence stored.** `EntityEdge` (`edges.py:263-291`) has no
   `confidence/score/trust` field; decisions-client confidence exists
   (`openai_decisions_client.py:359-365`) but is not persisted. Suggestion:
   store it + a trust ceiling until external confirmation (MAQS F8 pattern).
3. **P2 — no created_by/agent.** Nodes carry `group_id/created_at`, episodes
   carry source — but no agent identity on records; the `invalidated_by`
   link lives in memory only (`edge_operations.py:779-780`), not as an edge.
4. **P5 — hard delete, no tombstone.** `DETACH DELETE` (`nodes.py:122-127`);
   `remove_episode()` (`graphiti.py:2164-2192`) orphans nodes with
   `episode_count>1`. The retained expired edges are an *implicit* tombstone —
   making it explicit (zero-PII governance record) would close P5.
5. **B — transactions are driver-dependent.** Real commit/rollback only on
   Neo4j (`driver.py:147-160`); FalkorDB/Kuzu writes are immediate, bulk via
   `bulk_utils.py:138-139`. Plus quiet paths: `warning + continue/return None`
   on empty names, missing nodes, timestamp failure (`254-259, 319, 830-831`).
6. **Logging — no audit sink.** Only stdlib logging + PostHog usage stats
   (`telemetry.py:18-19`); OTel is optional with NoOp default. An append-only
   operation journal would close the Art12-shaped hole.

## Honest boundaries of this audit

- Nothing was executed: no FalkorDB instance, no residue measurement, no metric runs.
- Span inventory of OTel tracing was not exhaustively mapped.
- Comparison with the Mem0 audit (`docs/audits/mem0-way-audit.md`) is left to
  the reader; cross-system ranking is explicitly out of scope.

## Next steps

- Show the report to Graphiti authors via issue, give them time to respond.
- Their corrections/responses go in as a second commit to this file, findings are not rewritten.
