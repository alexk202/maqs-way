# Draft Issue for deep-thinking-lab/open-agent-memory-protocol (OAMP)

**Title:** Proposal: MAQS-Way uses OAMP §4.3 provenance binding as mandatory + adds measurable verification

**Body:**

Hi Jonathan / Deep Thinking team,

OAMP v1.2/v1.3 is the most precise provenance spec I've seen — `agent_id, session_id, timestamp, policy_id, source_hash, valid_from/valid_to, deletion_event signature chain` and §4.3 `entry.source.agent_id == oamp_agent_id` binding is exactly what audit needs.

We are building **MAQS-Way v0.1.3**, which adopts OAMP as provenance layer:

- Data model: OMPS base + OAMP mandatory binding
- Lifecycle: AMSP state machine + Graphiti bitemporal
- Verification: MAQS v1.6 audit + LoCoMo/LongMemEval + tombstone deletion lattice

**Proposal:** Reference MAQS-Way verification for OAMP governed-memory capabilities:
- `governance.provenance_query` capability → verified by cross-tenant negative test + R@5
- `deletion_event` → verified by 4-level lattice LOGICAL/PHYSICAL/SEMANTIC/MODEL

We have `maqs-way-standard.json` referencing OAMP fields and 7 conformance vectors including `invalid-001-no-agent-id` that fails OAMP §4.3.

Would you be open to adding MAQS-Way as verification example in `docs/governed-memory-interop-matrix.md`?

Best,
Aleksandr Kossarev
