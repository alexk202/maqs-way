# MAQS-Way v0.2.1 — Common Path from Policies to Implementation for Long-Term AI Memory

**Status:** v0.2.1 — evidence release (canon content unchanged from v0.2; honest: open known gaps listed in §7), normative file name `SPEC.md`, revision date 2026-10-27
**Author:** Aleksandr Kossarev
**Relation to MAQS:** MAQS v1.8.1 remains technical audit core (MAQS repo). Way is overlay: model + lifecycle + measurable verification.
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

`alive` and `critical` are profile extension fields (see `extensions`
in maqs-way-standard.json); they are not part of the core data model
(`schema_version way-v0.1.3`, frozen).


**E10 — Alive memory cap ([REC], MAQS E10).** The alive cap is
per-scope-per-subject: the cap applies within each memory scope for each
subject independently (scope anchor: `scope_enum` in
maqs-way-standard.json), never globally. Effect: `alive: true` exempts
the record from decay and summarization while the flag is set; it does
NOT block deletion (retention = `"legal_hold"` governs that, see
E10.alive_vs_hold below). Default overflow behavior: new protection is
DENIED (fail-closed for protection), the event is logged as
`cap_overflow {subject, scope, cap, attempted_id}`, and
`escalate_after_denials` consecutive denials escalate to the owner
(advisory, since E10 is [REC]). `escalate_after_denials` has no default
and MUST be declared by every system that enables the cap. The system
MUST NOT silently revoke existing protections and MUST NOT silently
reject new ones: default-FIFO eviction leaves `alive: true` set while
protection is actually gone — declaration outlives fact (silent-fail,
class B5); a lying flag is worse than forgetfulness. Opt-in only:
`overflow: evict_oldest` — explicit per-system configuration; each
eviction event MUST be logged with record id and reason (no silence even
opt-in). Opt-in explicitly redefines `alive` semantics (policy priority,
not absolute protection) and therefore is not a lie. Cap violations are
measurable (`alive_cap_overflow_rate`, P8 pattern) but non-blocking.


**E10 — alive vs legal hold (orthogonality).** `legal_hold` and `alive`
are orthogonal mechanisms: `legal_hold` (the existing retention value
`"legal_hold"`) blocks deletion (governance-level, hard); `alive`
protects against decay and summarization (significance-level, [REC]).
A record may carry both at once; neither implies the other. Hold does
not grant alive-protection and vice versa; removing one never removes
the other. Check: `is_forgettable(r) = not r.alive and r.retention !=
"legal_hold"`.


**E11 — Declared critical labels ([IMP], MAQS E11).** Critical status is
an explicit label with provenance (source: owner or authorized process).
No automatic importance inference: `importance` in canon is an F8
ceiling (a restriction), not a model field — no scale, no thresholds,
no source. Unlabeled records are treated as non-critical (no
reordering, no guessing); `unlabeled_ratio` is measured to keep the gap
visible. Unmarked blocks produce an explicit log ("0 critical blocks"),
never a silent pass-with-guessing.


**E11 — Placement verification.** `E11.verify_placement(context)` is a
structural audit (no LLM): every critical-labeled block MUST occupy head
or tail zones (first / last `critical_zone_fraction` of assembled
context tokens, default 0.15; owner: E11; calibration → v0.4 list);
middle-zone critical placement = FAIL. Semantic adequacy of zone sizes —
deferred (v0.4 list).


Glossary (frozen; redefinition only via separate sanction):
`alive`/`protected` — declared, not inferred; `critical` — explicit
label with provenance (declared, not inferred); `head`/`tail zones` —
first/last `critical_zone_fraction` of assembled context tokens;
`unlabeled_ratio` — reported, not gated; "positioning" here means the
placement procedure for critical blocks (head/tail zones + positional
audit), not the bare word.

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

`threshold`, `window {type, size}`, `action` and the equality keys of
the class counters below are policy extension settings (see
`extensions.policy` in maqs-way-standard.json); they are not part of the
core data model (`schema_version way-v0.1.3`, frozen). Alert journals
and escalation entries reuse the existing logging infrastructure
(hash-chained, retention per `logging.retention`); no new data-model
fields are introduced.

Every class counter declares THREE independent literals (never glued):
threshold N, window {type, size}, action. Threshold and window are
independently tunable. Window types: `sliding` (events within a trailing
window) | `tumbling` (fixed buckets); `sliding` is the default window
type, `tumbling` requires an explicit per-deployment declaration. Every
counter declares its equality key (signature): without a key, "identical"
is undefined and the counter is nondeterministic — such a counter is
rejected.

**I10 — Noise budget ([IMP], MAQS I10).** Declared parameters (owner:
I10): `threshold` 3 (default), `window` {sliding, 5m} (defaults),
equality key "warning text", `action` "aggregate". The same warning
repeated N+ times per interval is aggregated with a counter — N
identical warnings become one record + count, never emitted individually
past the threshold; after N identical warnings, deduplicate or escalate
to a different level. B5-link: claimed success on unperformed work is a
B5-class failure, detected as a pure function of (claimed_events,
performed_actions) over a declared `work_sink` (recorded side-effects;
no default — MUST be declared when the check is applied, owner: I10);
claimed success + empty sink → RED. I10 exists to prevent duplicate
noise from masking false success.

**I11 — Recovery loop ([CRIT], MAQS I11).** Declared parameters (owner:
I11): `threshold` 3 (default), `window` {sliding, 10m} (defaults),
equality key "exit code", `action` "halt+alert". Any automatic restart
(systemd/supervisor/self-heal) must be accompanied by a diagnostic trace
of the root cause. A recovery cycle without diagnosis is prohibited:
after N repetitions without diagnosis — halt and alert, never eternal
restart. Halt stops the OWN process; halt-without-alert is forbidden
exactly like restart-without-diagnosis. The alert sink is a REAL
persistent store (journal file / syslog; no default — MUST be declared,
must be readable after halt, owner: I11), never bare stderr/exit code:
stderr does not survive halt, exit code is visible to the parent only.
An alert that cannot be read after halt is a silent-fail (class B5).
Verification reads the trace AFTER halt from the sink.

**I12 — Escalation budget ([CRIT], MAQS I12).** Declared parameters
(owner: I12): `threshold` 3 (default), `window` {sliding, 1h}
(defaults), equality key "dependency + error code", `action` "escalate".
A repeated dependency failure with identical signature escalates after
N occurrences (alert / halt / flagged degradation) — never polls
indefinitely. Escalate targets EXTERNAL dependencies (no right to stop,
voice only) and is REPEATABLE on a schedule — a notification contract,
not a one-shot shout; the repeat schedule has no default and MUST be
declared (owner: I12). Escalation without a journal entry is a
B5-failure (same class as halt-without-alert). A system aware of a
failure that does not escalate degrades silently.

**Halt / escalate boundary.** Halt applies to the own process (right to
stop = obligation to alert); escalate applies to external dependencies
(no right to stop, voice only). On conflict (both conditions met): halt
dominates (safety) + escalate the owner. A `flagged degradation` MUST be
observable in the sink — otherwise the degradation is silent = B5.

Adjacent, not covering: SPEC §2.3 (appeal-escalation + operator SLA)
shares vocabulary only (different trigger, different mechanism); closing
this gap with "already in §2.3" is rejected in advance.

Deferred (v0.4 list): per-scope/per-subject counter partitioning (cf.
E10 cap semantics); per-deployment tumbling-window adoption.

Glossary (frozen; redefinition only via separate sanction):
`policy triple` — threshold + window {type, size} + action, three
independent literals, never glued; `equality key` (signature) — the
declared field that defines "identical" events; `work_sink` — declared
store of recorded side-effects; `alert sink` — persistent store holding
the halt alert, readable after halt; `halt` — stop of the own process;
`escalate` — notification contract to external dependencies, repeatable
on a declared schedule.

### 3.5 Reporting

config: system config, embedding model version, policy version
standard_version: MAQS 1.8.1 + Way 0.2.1
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


## 5. Mapping to MAQS v1.8.1

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

1. This file is `SPEC.md` v0.2.1 — normative file name, status evidence release (canon content unchanged from v0.2; open gaps listed in §7).
2. Backlog v0.3 (retargeted from v0.2 by release decision 1.8 — no silent rollover):
   - Canonization of formulations with owner signature: B4 write atomicity (§2.5), E10/E11, I10/I11/I12, I14, I15, P9/P10, 0.5a/0.6a drift thresholds
   - `deletion_marker` in JSON data_model: confirm obsolete-by-separation (§2.1 note) or specify (open question, not silently dropped)
   - `identity_signature`: Ed25519 over canonical JSON — full specification (moved out of data-model example, §2.1)
   - `operator` role: full permission matrix for §2.3 (review, appeal, override boundaries)
   - Executable behavioral harness (LoCoMo/LongMemEval runs) + D9 behavioral test
   - Live verification of all 11 external links in `docs/landscape.md` + per-row `verified: ✅/⏳/❌` column
   - P/V/E alignment for Architecture and Verification layers (§2, §3)
3. Open discussions with OMPS/AMSP/OAMP authors — propose MAQS as verification layer

## 7. Change Log

- **v0.1 → v0.1.1 (2026-10-10):** external review (way.md) + internal review incorporated. Section 0.1 deduplicated to landscape.md reference; file name/status conflict resolved; incidents added to all 8 principles; thresholds marked indicative; P/V/E pattern applied to Principles layer; embedding provenance added; conflict resolution policy per profile; temporal priority documented; lifecycle completed; Policy Broker split into decision+mode; scope notation canonicalized; legal_hold added; logging retention justified; latency cost documented; Recoverability/Portability added to golden set; licenses note added; subject enum introduced; confidence_after added; links extended; title «Universal» → «Common»; deletion_marker separated from live record; broker appeal path added; D9 explained.
- **v0.1.1 → v0.1.2 (2026-10-10):** internal review: §2 header restored (ARCHITECTURE Layer); `status` returned as derived view (not stored field); lifecycle completed with EXPIRED → ARCHIVED and ARCHIVED → ACTIVE (restore); inline `(fixes Cx)` references replaced by §7 Change Log; Profile C P6 collision fixed (MAQS P6 isolation test + Way/MAQS numbering note); Author line added to header; §3 claim scoped honestly; `operator` role defined in §2.3 (matrix — TODO v0.2); `identity_signature` TODO removed from JSON example, moved to Backlog §6.2.
- **v0.1.2 → v0.1.3 (2026-10-10):** hardening sync with `maqs-way-standard.json`. Thresholds split into CI gate / target pair (§1 P3, §1 P8, §3.2) — canon from JSON `verification_suite.metrics`; values remain expert/indicative until first real run. `provenance.visible_to` added (§2.1) as mechanism for semantic masking. New §2.2 *Temporal priority* section added, closes dangling reference from §2.1; step-3 correction (`invalid_at < now` → `EXPIRED`, not `SUPERSEDED`) mirrored in JSON. `operator` SLA 72h added (§2.3). OTel allowed/forbidden keys added (§3.4). `shared_fact_visibility_leak` added to negative scenarios (§1 P8). `masked` as lifecycle state — **rejected**; masking is a visibility operation (`visible_to`), not a state. `schema_version` → `omps-0.1.0+way-v0.1.3`. CRIT sync (direct, sanctioned): G1 (fixtures §2.3 + JSON negative_scenarios +3), I13 (credential-in-URL redactor §3.4 + JSON sanitization), D8 (§2.5), F8 (§2.4), E12 (§2.4), H5 (§2.5 + evals), J3 (§3.5 j3_guard).
- **v0.1.3 → v0.1.4 (2026-10-10):** schemas package landed (`schemas/memory-item.schema.json` + `schemas/check_conformance.py`, gate green); `data_model.$ref_status` provisional → active. Release stamps bumped; data model (`schema_version way-v0.1.3`), thresholds, algorithms, vectors unchanged — semantic diff empty by design.
- **v0.1.4 → v0.2 (2026-10-15, owner signature):** production ladder stage 1 closed — packages 1.1 (C8 gate) → 1.2 (B gate) → 1.3 (vectors 7→12) → 1.4 (audit CLI v0.1 + namespaces) → 1.5 (E10/E11 formulation) → 1.6a–d (I-counters/handlers/layers, I13 proven, C8 bridge consolidated) → 1.7a/b (audit procedure, pipeline hygiene) + LICENSE (Apache-2.0 sync). Closed in release: formulation+gates for all listed MAQS items. OPEN known gaps (retargeted v0.2→v0.3 by this release decision, no silent rollover): B4 write atomicity (→§2.5), E10/E11 canonization, I10/I11/I12 canonization, I14, I15 canonization, P9/P10 canonization, 0.5a dead-code rule, 0.6a drift thresholds (12 total). `schema_version way-v0.1.3` FROZEN (model unchanged across 1.1–1.7 — asserted fact). Release ships as honest minor WITH this list; silence about gaps would be false green.
- **v0.2 → v0.2.1 (2026-10-27, owner signature):** evidence release — canon content unchanged from v0.2; the only canon-adjacent delta since v0.2 is the MAQS reference sync v1.6 → v1.8.1 (header relation line, §3.5 standard_version, §5 heading; `maqs_core_reference` in JSON; version references only — no formulation, threshold, or vector changes). The release fixes the evidence accumulated since v0.2 and provides an externally referenceable tag + DOI. Key evidence (numbers from repo files): full-500-iso headline evidence-R@5 = 0.988 (494/500, Wilson [0.974, 0.994]) — the FIRST isolated full-500 run (the 2026-10-17 pre-isolation 0.992 stays in history with the confound annotation); the shared-history confound (mem0) was found by the H5 [CRIT] guard, measured (14.8% genuine tail facts in the frozen g1 store, 249/1680 — extraction-channel contamination), and eliminated by per-question history isolation in all runners; P4 verified on mem0@0724291b (Linux CPU-only stub stand; boundary: the extraction-prompt path with a real LLM was not exercised); determinism boundary documented in REPRODUCE §0 (byte-identity is a window property on the reference stand; cross-stand untested — compare in bands); full reproduction recipe (evals/REPRODUCE.md); config fingerprint (CONFIG_SHA256) in all runners; prereg template v1.1. OPEN known gaps: unchanged 12 from v0.2, target v0.3 — B4 write atomicity (→§2.5), E10/E11 canonization, I10/I11/I12 canonization, I14, I15 canonization, P9/P10 canonization, 0.5a dead-code rule, 0.6a drift thresholds (12 total). `schema_version way-v0.1.3` FROZEN (model unchanged — asserted fact).
- **v0.2.1 → v0.3 (in progress):** E10/E11 canonized in §2.4 (owner signature 2026-10-27); fields as profile extensions, core data model unchanged (way-v0.1.3); I10/I11/I12 canonized in §3.4 (owner signature 2026-10-27); parameters as policy extensions, core data model unchanged (way-v0.1.3).

> Check not that the mechanism exists. Check that it works.
