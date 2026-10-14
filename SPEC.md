# MAQS-Way v0.1.4 — Common Path from Policies to Implementation for Long-Term AI Memory

**Status:** v0.1.4 — experimental, normative file name `SPEC.md`, revision date 2026-10-10
**Author:** Aleksandr Kossarev
**Relation to MAQS:** MAQS v1.6 remains technical audit core (MAQS repo). Way is overlay: model + lifecycle + measurable verification.
**License note:** Sources referenced under their respective licenses. This spec is Apache-2.0.

## 0. Industry Diagnosis

**What exists:**
- **Policy layer:** GDPR Art17, EU AI Act Art12/13/19, RBAC — surplus of what *should* be
- **Audit layer:** MAQS — checklist how to ensure it does not break, each CRIT backed by production incident

**What is missing:**
- **Path layer:** which tools, patterns, schemas to implement policy and how to prove it works

### 0.1 Landscape Scan — summary

Full scan is maintained in `docs/landscape.md` (single source of truth, dated 2026-10-10, 11 families verified). This section is summary only to avoid desync.

- **Portability:** OMPS `rdh073/omps` — memory-item.schema.json, deletion-marker.schema.json
- **Lifecycle/Scope:** AMSP `sanej/amsp` — active→deleted, user-portable, team-shared
- **Provenance:** OAMP `deep-thinking-lab` — agent_id binding §4.3 mandatory
- **Transport:** MCP Memory Servers — Entity/Relation, flat file per instance
- **Governance:** MemoryOps AI `patibandlavenkatamanideep/memoryops-ai` — 10 invariants, Policy Broker
- **Vector extract:** Mem0/Mem0g arXiv:2504.19413 — ADD/UPDATE/DELETE/NOOP, gap provenance-erased
- **Bitemporal KG:** Zep/Graphiti `getzep/graphiti` arXiv:2501.13956 — valid_at/invalid_at + t'_created/t'_expired, invalidation-on-contradiction
- **Deletion verification:** Tombstone `poojan6216/tombstone` — 6-tier cascade, bench native delete 92-100% recoverable
- **Eval:** LoCoMo, LongMemEval (with abstention), MemoryAgentBench
- **Security:** OWASP LLM Top10, OWASP Agentic ASI06 Memory Poisoning, MITRE ATLAS AML.T0080
- **Observability:** EU AI Act Art12 + OTel GenAI semconv

See `docs/landscape.md` for concrete artifacts and verification status of each link (live check required before publication; per-row `verified: ✅/⏳/❌` column to be maintained in landscape.md).

---

## 1. PRINCIPLES Layer

**Structure per principle (P/V/E pattern applied to this layer from v0.1.1; Architecture and Verification layers aligned to the same pattern in v0.2):**
- Property (mandatory): what must hold
- Verification (how to check): test, metric, negative scenario
- Example (non-normative): hint
- MAQS link + incident (showing lineage MAQS → Way)

> Thresholds in this version are **indicative engineering targets, subject to revision after first real run**. Normative thresholds in v0.2.

### P1 Veracity — memory is data, not instruction

- **Property:** Every memory record is typed data, not executable instruction. Model output must be typed `source.type=model_output` and must not increase trust on summarization/transformation.
- **Verification:** OWASP ASI06-001 false-fact injection probe → Policy Broker BLOCK 100% (indicative). Fenced `<retrieved_context type=...>`. Transformation must preserve `confidence_after ≤ confidence_before` for model_output.
- **Example:** `fenced retrieved_context + policy broker BLOCK`
- **MAQS link:** E6 (trust escalation on summarization), F1–F8 feedback loop, F7 admitted≠trusted. **Incident:** traceback where agent summarized its own error report and escalated confidence from 0.6 to 0.9, leading to loop.

### P2 Provenance — every record traces back

- **Property:** Each record carries who created, when, source ref+hash, policy_id/version, confidence, transformation history. Mutations append provenance, never replace origin.
- **Verification:** Schema validation against OMPS memory-item.schema.json extended with OAMP §4.3 binding `source.agent_id == provenance.created_by.id` mandatory. `identity_signature` = Ed25519 over canonical JSON (specification deferred to v0.2, see Backlog §6.2).
- **Example:** OMPS provenance + OAMP agent_id, session_id, source_hash
- **MAQS link:** B (write integrity), 0 Map. **Incident:** orphaned vectors without source after migration, impossible to audit.

### P3 Controlled Aging — forget outdated, keep relevant

- **Property:** Memory decays stale, refreshes on use, supersedes on contradiction, expires on TTL, without displacing relevant.
- **Verification:** Golden set temporal accuracy CI gate ≥65%, target ≥80% (LoCoMo temporal + Graphiti valid_at); knowledge update accuracy after supersession ≥70% (LongMemEval); no fresh evicted before stale.
- **Example:** Graphiti bitemporal `valid_at/invalid_at` (when fact true) + `t_created/t_expired` (when learned)
- **MAQS link:** D Retrieval, C Growth. **Incident:** volume doubling after decay job removed fresh facts due to timestamp confusion.

### P4 Isolation — boundaries verified by negative tests

- **Property:** Tenant/user/project/agent boundaries enforced, including vector search path, not just filter presence.
- **Verification:** Negative test `cross_tenant_retrieval_returns_0` leak=0 (indicative). Includes vector path. Must cover embedding provenance. G1 requires 4 fixtures (§2.3): independent callers, wrong/omitted scope, read-only write attempt, access after revocation.
- **Example:** MemoryOps invariant #1 + AMSP scope model
- **MAQS link:** G Isolation. **Incident:** search returned User A memory to User B because pgvector filter applied after top-k.

### P5 Deletability — deletion propagates everywhere

- **Property:** Deletion propagates to replicas, vector indexes, caches, derived summaries. Tombstone preserved with zero personal data.
- **Verification:** Deletion lattice LOGICAL/PHYSICAL/SEMANTIC/MODEL, residue 0.0% indicative (tombstone bench). Deletion = 6-tier cascade `graph_edges → nodes_if_sole_provenance → embeddings_fk → facts_fk → artifacts → rounds` in one PG transaction + best-effort graph reconciliation. `cascade only if sole provenance` — if NOT sole, edge removed, node kept.
- **Example:** deletion_log(request_id, timestamp, scope, layer_counts, requestor) Ed25519-signed, hash-chained, layer_counts for audit
- **MAQS link:** B, G. **Incident:** GDPR deletion removed row but Qdrant rebuild survivors kept embedding recoverable 100%.

### P6 Recoverability — backup + verified restore

- **Property:** Backup, versioning of schemas/embeddings, idempotent migrations, verified restore procedures.
- **Verification:** Restore drill quarterly, hash equality of restored store vs backup manifest. Embedding compatibility check: model versioned, mismatch → fallback keyword-only `retrieval_mode=fallback`.
- **Example:** MAQS P1 backup + versioned embedding model
- **MAQS link:** H, I. **Incident:** embedding model upgraded, all old vectors mismatched, retrieval fell back to empty without alert.

### P7 Portability — user's memory belongs to user

- **Property:** User memory exportable/importable without transformation, with consent and sensitivity preserved, provenance intact.
- **Verification:** Round-trip `export→import` → 0 losses of provenance + consent fields, hash equality. Uses OMPS memory-bundle.schema.json + AMSP export/import.
- **Example:** OMPS bundle
- **MAQS link:** New from OMPS/AMSP. **Incident:** export stripped source hash, import created duplicate with new id.

### P8 Measurability — prove it works, not that mechanism exists

- **Property:** Quality measured on representative tasks including negative cases.
- **Verification:** Eval harness LoCoMo/LongMemEval/MemoryAgentBench + negative scenarios cross_tenant_leak, prompt_injection_via_memory, feedback_contamination, stale_overrides_fresh, shared_fact_visibility_leak. Metrics indicative until first run (CI gate / target): R@5 ≥0.7 / ≥0.85, abstention ≥0.8 / ≥0.9 when no evidence, duplicate ≤5% / ≤2%, contamination ≤1% / 0%.
- **Example:** Golden set + LLM-judge + R@k + limitations description (what metric does not see)
- **MAQS link:** D9 extended (D9 = agent self-report diagnostic, see MAQS D9). **Incident:** D9 existed but no behavioral test, system passed checklist but failed temporal recall in prod.


## 2. ARCHITECTURE Layer — Which properties must be implemented

### 2.1 Data Model

Uses OMPS schema as canonical. `schema_version` field explains provenance. `status` is a derived view from lifecycle events (see §2.2), not a stored field:

```json
{
  "schema_version": "omps-0.1.0+way-v0.1.3",
  "id": "mem_001",
  "type": "preference | episode | semantic | procedural | project | system",
  "subject": {"type": "user | agent | team | org | system", "id": "user_123"},
  "scope": {"type": "user-portable | agent-private | team-shared | org-shared | local-session"},
  "content": {"format": "text/plain", "value": "...", "language": "en"},
  "sensitivity": "low | medium | high | secret",
  "consent": {
    "basis": "explicit_user_request | inferred | imported",
    "exportable": true,
    "shareable_with_agents": true,
    "usable_for_personalization": true,
    "usable_for_training": false,
    "requires_confirmation_before_use": false
  },
  "retention": {"mode": "until_deleted | ttl | sliding_window | legal_hold", "ttl_days": 90, "valid_from": "...", "valid_to": "..."},
  "provenance": {
    "created_at": "2026-10-10T00:00:00Z",
    "created_by": {"type": "agent", "id": "agent_001"},
    "source": {"type": "conversation | file | web | agent | model_output", "ref": "conv_123", "hash": "sha256:..."},
    "policy_id": "policy_v2",
    "policy_version": "1.3",
    "confidence": 0.92,
    "confidence_after": 0.92,
    "transformation_history": [{"op": "summarize", "from": "mem_000", "at": "...", "agent_id": "...", "confidence_after": 0.85}],
    "sources": [{"agent_id": "...", "session_id": "...", "task_id": "...", "timestamp": "..."}],
    "visible_to": ["user_123", "agent_001"]
  },
  "embedding": {"model": "qwen3-1024", "version": "1.0", "derived_from_trust": "low", "vector_id": "..."},
  "revision": 3,
  "links": {"supersedes": "mem_000", "derived_from": ["episode_123"], "invalidated_by": null, "contested_by": null}
}
```

**Note:** deletion_marker is NOT a field of a live record — it is a separate artifact governed by OMPS `deletion-marker.schema.json`, created only at deletion time and preserved in the governance tombstone (structure: `request_id, timestamp, scope, layer_counts, requestor, signature: ed25519:...`). Shown in P5 example for schema awareness only.

**Data model notes:**
- **schema_version:** `"omps-0.1.0+way-v0.1.3"` — `omps-0.1.0` base + `way-v0.1.3` extension, semver extension documented.
- **status:** derived view from lifecycle events (§2.2), not a stored field — computed as projection of the latest lifecycle event per record.
- **identity_signature:** removed from the live-record example; specification (Ed25519 over canonical JSON) deferred to v0.2 — see Backlog §6.2.
- **Scope notation:** accepts both `user.portable` and `user-portable` — canonical is `user-portable` (AMSP), mapping table in `docs/mapping-to-maqs.md`.
- **visible_to:** array of `subject.id` for which the record is visible. Mechanism for semantic masking (§2.2): on deletion of a shared fact, the requestor is removed from `visible_to`; empty array → physical delete. `visible_to` absent = unrestricted within scope.
- **Bitemporal vs retention:** `valid_at/invalid_at` = when fact true in world (Graphiti), `retention.valid_from/valid_to` = when we store it. Priority: world time for reasoning, retention time for lifecycle. See §2.2 *Temporal priority*.
- **legal_hold:** added to retention for Profile B where Delete not executable during hold.

### 2.2 Lifecycle

State machine complete:

ACTIVE → STALE (decay) → ACTIVE (refresh)
ACTIVE → CONTESTED (conflict) → SUPERSEDED (resolve, policy: for Profile A User Wins, for B Policy Broker wins, for C no contest)
ACTIVE/STALE → EXPIRED (policy ttl) → ARCHIVED (soft archive, state change, not physical deletion)
ARCHIVED → ACTIVE (restore, if recoverable and policy permits)
Any → DELETED (user delete / GDPR Art17, except legal_hold) → TOMBSTONE (soft, content+embedding cleared, governance tombstone preserved) → null (compaction hard, Ed25519-signed)

If sole provenance: node deleted, else edge removed.

Conflict resolution policy:
- Personal Assistant: User Wins, new fact supersedes contested with link `supersedes`.
- Enterprise: Policy Broker decides `decision: SAVE|PENDING_APPROVAL|BLOCK|DROP_LOW_UTILITY` + `mode: APPEND|UPDATE_EXISTING|MERGE_WITH_EXISTING` (two orthogonal fields). Broker decision is appealable: contested records may be escalated to human review; appeal outcome appends provenance, never silently overrides broker entry. Role of the reviewing human = `operator` (defined in §2.3; full operator permission matrix — TODO v0.2).
- Ephemeral: no writes, so no contest.

**Temporal priority.** When world time (`valid_at`/`invalid_at`) and retention time (`retention.valid_from`/`valid_to`) disagree, resolution follows the canonical algorithm in `maqs-way-standard.json` → `lifecycle.temporal_priority_algorithm` (5 steps) — not restated here to avoid desync. Summary:
- `legal_hold` blocks deletion regardless of world time
- retention expired (`retention.valid_to < now`) → `EXPIRED`
- world time says fact no longer true (`invalid_at < now`) → `EXPIRED` — **not** `SUPERSEDED`; supersession is a conflict-resolution outcome (see state machine above), not an automatic time effect
- otherwise `ACTIVE`/`STALE` by decay
- reasoning filter: retention valid AND `valid_at ≤ now` AND (`invalid_at` null or `> now`)

### 2.3 Access Control

- Scope model from AMSP formalized, canonical `user-portable` etc.
- Policy Broker split: `decision: SAVE|PENDING_APPROVAL|BLOCK|DROP_LOW_UTILITY` + `mode: APPEND|UPDATE_EXISTING|MERGE_WITH_EXISTING` — orthogonal.
- **operator role:** a human actor who reviews escalated/appealed broker decisions and contested records. May read contested records and confirm/override appeal outcomes; each action appends provenance. Full permission matrix — TODO v0.2.
- **operator SLA:** review within 72h for escalated/appealed decisions and contested records in Profile B (recommended, not a global normative requirement).
- **G1 fixtures (required, MAQS G1 [CRIT]):** boundary proved by attempted violations, not filter presence: (1) independently authenticated callers A vs B, (2) wrong or omitted scope, (3) read-only caller attempting write → BLOCK, (4) access after membership revocation → BLOCK. Single-scope pass-through is not a boundary.

### 2.4 Context Assembly

- MAQS E: blind truncation prohibited, budgets, positioning
- Content-as-Data: fenced `<retrieved_context>` with typing
- Feedback guard: model_output → ingestion only via Extractor + secret/PII check
- **F8 ceiling (MAQS F8):** records with `source.type=model_output` cannot receive importance above defined ceiling until confirmed by external source or user.
- **E12 artifact precedence (MAQS E12):** current artifact retains factual precedence over memory; conflict stays observable, memory must not silently substitute or reconstruct the artifact representation.

### 2.5 Resilience

- Contracts between stores, versioned schemas/embeddings, idempotent migrations
- Embedding provenance: `embedding.derived_from_trust` inherits from source, embedding does NOT clean origin
- **D8 incompatible embeddings (MAQS D8 [CRIT]):** dimension/language mismatch → explicit rejection with diagnostics, not a burst of warnings during search; re-index or migrate before mixed-model retrieval.
- **H5 test isolation (MAQS H5 [CRIT]):** tests use temp/in-memory stores and mocked APIs, never write to live memory; isolation covers filesystem (no prod paths as defaults); guard check before/after confirms no test artifacts leaked.


## 3. VERIFICATION Layer

**Structure:** P/V/E pattern applied to Principles layer (§1) from v0.1.1; Architecture and Verification layers aligned to the same pattern in v0.2.

### 3.1 Separation P/V/E

Each item follows Property/Verification/Example (see §1 for the applied pattern; example items in §1 P1–P8).

### 3.2 Measurable Quality — indicative targets

**A checklist confirms mechanism exists. Way requires proving it works.**

| Property | Test | CI gate (min) | Target | Source |
|---|---|---|---|---|
| Retrieval accuracy | LoCoMo single/multi-hop; LongMemEval oracle | R@5 ≥0.7 | R@5 ≥0.85 | LoCoMo, LongMemEval |
| Knowledge update † | LongMemEval updates, FactConsolidation | — | ≥0.7 | LongMemEval, MemoryAgentBench CR |
| Temporal reasoning | LoCoMo temporal, Graphiti valid_at | ≥0.65 | ≥0.8 | Graphiti |
| Abstention | LongMemEval abstention | ≥0.8 | ≥0.9 | LongMemEval |
| Deduplication | Duplicate injection | ≤5% | ≤2% | MemoryOps |
| Context contamination | Feedback loop probe | ≤1% | =0 | MAQS F |
| Deletion | Tombstone cascade | 0.0% residue | 0.0% | tombstone bench |
| Shared-fact masking § | After delete of shared fact, requestor cannot retrieve | 0 leak | 0 | Way P5 (§2.2) |
| Isolation | Cross-tenant retrieval | 0 leak | 0 | MemoryOps #1 |
| Poisoning | OWASP ASI06-001/002 | BLOCK 100% | BLOCK 100% | OWASP Agentic |
| Recoverability | Restore drill | hash equality | hash equality | MAQS H |
| Portability | Export→import round-trip | 0 loss | 0 loss | OMPS |


All thresholds marked **indicative, subject to revision after first run on real system**; `min` = CI gate (below → fail pipeline), `target` = engineering goal. Canonical source: `maqs-way-standard.json` → `verification_suite.metrics`.
† Knowledge update target from §1 P3 — not yet in JSON `metrics`, to be added in v0.2 (see §6).
§ From JSON `verification_suite.negative_scenarios`, merged with its metric.

### 3.3 Deletion Verification Lattice

- LOGICAL: search() returns 0
- PHYSICAL: DELETE+REINDEX+VACUUM FULL pgvector, rebuild survivors Qdrant, zero HNSW slots Chroma — verified by file scan
- SEMANTIC: embedding similarity <0.3, MIA fails
- MODEL: extraction probe fails
Each Ed25519-signed receipt, replayable. Deletion_log zero PII.

### 3.4 Logging

- What to log (Art12/19): period of use start/end, reference DB checked, input leading to match, natural persons involved, agent identity, policy_version, classification, outcome, precise timestamp, signature
- How: OTel GenAI `gen_ai.operation.name`, `gen_ai.conversation.id`, `gen_ai.tool.name`, `gen_ai.usage.*`, `gen_ai.client.inference.operation.details` (opt-in PII)
- **Sanitization (hardened):** `gen_ai.client.inference.operation.details` — allowed: `tool_args_sanitized`, `retrieval_count`, `policy_decision`, `latency_ms`; forbidden: `raw_content`, `secret`, `PII`, `embedding_vector`. Secret/PII filter applied before logging, same rule as Policy Broker. Includes credential-in-URL (`?token=...`, `bot<id>:AA...` in path) — masked by redactor before write (MAQS I13 [CRIT]).
- Tamper-evident: hash-chained, Ed25519, WORM lock for regulated tenants, retention 12 months default, 6 years configurable for regulated (source: EU AI Act Art12 says 6 months min, Way extends for regulated Profile B, documented). Note: committed before response returns adds latency cost ~5-15ms.
- Sources referenced under their respective licenses.

### 3.5 Reporting

config: system config, embedding model version, policy version
standard_version: MAQS 1.6 + Way 0.1.4
test_scenarios: LoCoMo/LongMemEval/MemoryAgentBench + negative + deletion lattice + restore drill + round-trip
results: per-metric + per-invariance + limitations
exceptions: documented per-item with justification
residual_risks: open issues
remediation_plan: priority order
j3_guard: every fix closed with regression guard test; unexecuted test (silent skip, async without runner) = incomplete (MAQS J3)


## 4. Application Profiles

- **Profile A: Personal Assistant**: scope user-portable, strict consent, evaluation LoCoMo+LongMemEval, deletion LOGICAL+PHYSICAL, conflict resolution User Wins
- **Profile B: Enterprise**: tenant isolation, policy broker, 10 invariants, EU AI Act logging, deletion full lattice, OTel, legal_hold support, broker appealable to human review (operator role, §2.3)
- **Profile C: Ephemeral**: no write, no retrieval, verified by MAQS P6 isolation test (note: in Way, isolation is P4, recoverability is P6 — numbering differs between standards; mapping in `docs/mapping-to-maqs.md`)

Each profile is subset of Way + refs to MAQS items.


## 5. Mapping to MAQS v1.6

0 Map → 2.1 data model + provenance
A Input validation → 2.4 Content-as-Data + OWASP ASI06
B Write integrity → 2.2 lifecycle + tombstone + OAMP binding
C Growth → 2.2 state machine + bitemporal
D Retrieval → 3.2 measurable quality
E Assembly → 2.4 fenced context + blind truncation ban
F Feedback → 2.4 guard typed
G Isolation → 2.3 scope + negative tests
H Concurrency → 2.5 embedding versioning
I Observability → 3.4 OTel + Art12
J Change Management → 3.5 reporting + regression guard

I7 diagnostic self-interrogation → supplementary signal, not evidence.


## 6. Next Steps

1. This file is `SPEC.md` v0.1.4 — normative file name, status experimental but versioned.
2. Backlog v0.2:
   - Formal `schemas/memory-item.schema.json` extending OMPS — required
   - `identity_signature`: Ed25519 over canonical JSON — full specification (moved out of data-model example, §2.1)
   - `operator` role: full permission matrix for §2.3 (review, appeal, override boundaries)
   - Expand `maqs-way-standard.json` to include deletion_marker (as separate artifact per 2.1 note) + embedding provenance
   - `maqs-way audit CLI` v0.1 shipped (`schemas/maqs_way_audit.py`: schema + manifest + lint + coverage, namespaces, canon-pin) + conformance vectors (12 in manifest: schema 4/4, behavioral-declared 8/8; executable harness → v0.2)
   - Behavioral test for D9 (MAQS D9 — agent self-report diagnostic): golden set from LoCoMo/LongMemEval (closest point where mechanism meets result)
   - Live verification of all 11 external links in `docs/landscape.md` + per-row `verified: ✅/⏳/❌` column
   - P/V/E alignment for Architecture and Verification layers (§2, §3)
3. Open discussions with OMPS/AMSP/OAMP authors — propose MAQS as verification layer

## 7. Change Log

- **v0.1 → v0.1.1 (2026-10-10):** external review (way.md) + internal review incorporated. Section 0.1 deduplicated to landscape.md reference; file name/status conflict resolved; incidents added to all 8 principles; thresholds marked indicative; P/V/E pattern applied to Principles layer; embedding provenance added; conflict resolution policy per profile; temporal priority documented; lifecycle completed; Policy Broker split into decision+mode; scope notation canonicalized; legal_hold added; logging retention justified; latency cost documented; Recoverability/Portability added to golden set; licenses note added; subject enum introduced; confidence_after added; links extended; title «Universal» → «Common»; deletion_marker separated from live record; broker appeal path added; D9 explained.
- **v0.1.1 → v0.1.2 (2026-10-10):** internal review: §2 header restored (ARCHITECTURE Layer); `status` returned as derived view (not stored field); lifecycle completed with EXPIRED → ARCHIVED and ARCHIVED → ACTIVE (restore); inline `(fixes Cx)` references replaced by §7 Change Log; Profile C P6 collision fixed (MAQS P6 isolation test + Way/MAQS numbering note); Author line added to header; §3 claim scoped honestly; `operator` role defined in §2.3 (matrix — TODO v0.2); `identity_signature` TODO removed from JSON example, moved to Backlog §6.2.
- **v0.1.2 → v0.1.3 (2026-10-10):** hardening sync with `maqs-way-standard.json`. Thresholds split into CI gate / target pair (§1 P3, §1 P8, §3.2) — canon from JSON `verification_suite.metrics`; values remain expert/indicative until first real run. `provenance.visible_to` added (§2.1) as mechanism for semantic masking. New §2.2 *Temporal priority* section added, closes dangling reference from §2.1; step-3 correction (`invalid_at < now` → `EXPIRED`, not `SUPERSEDED`) mirrored in JSON. `operator` SLA 72h added (§2.3). OTel allowed/forbidden keys added (§3.4). `shared_fact_visibility_leak` added to negative scenarios (§1 P8). `masked` as lifecycle state — **rejected**; masking is a visibility operation (`visible_to`), not a state. `schema_version` → `omps-0.1.0+way-v0.1.3`. CRIT sync (direct, sanctioned): G1 (fixtures §2.3 + JSON negative_scenarios +3), I13 (credential-in-URL redactor §3.4 + JSON sanitization), D8 (§2.5), F8 (§2.4), E12 (§2.4), H5 (§2.5 + evals), J3 (§3.5 j3_guard).
- **v0.1.3 → v0.1.4 (2026-10-10):** schemas package landed (`schemas/memory-item.schema.json` + `schemas/check_conformance.py`, gate green); `data_model.$ref_status` provisional → active. Release stamps bumped; data model (`schema_version way-v0.1.3`), thresholds, algorithms, vectors unchanged — semantic diff empty by design.

> Check not that the mechanism exists. Check that it works.
