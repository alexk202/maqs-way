# I15 Layer Taxonomy Formulation (v0.1, NOT canon)

> Status: formulation proposal, package 1.6d. NOT normative until v0.2
> canonization with owner signature. I15 is a known gap
> (owner: 1.6d-formulation, closes_in: v0.2 canonization).
> Core rule: diagnose → layer → interpret. Never interpret without a layer.

## Taxonomy (closed enum, growth by owner decision)

Exactly 3 layers — they exhaust lifetime categories:
- **persistent**: long-lived memory store (SPEC §2.1 records).
- **session**: current conversation context.
- **transient**: ephemeral, no persistence guarantee.

Extension = new owner decision (precedent: scope_enum, whitelist 1.4,
catalog 1.6c). `unknown` is NOT a 4th layer — it is an honest diagnostic
state (unclassifiable input is a fact).

## Layer assignment (declared, not inferred)

Layer is a DECLARED property of the query/record (metadata set at creation
by the request creator). `identify(query)` READS the declared layer;
it does NOT infer it. Inferring a layer ("looks like session") is a label
without source → RED (rule #5, label class). No declaration → `unknown`,
never a guess. Silent default substitution (e.g. quiet `session`) = level
substitution, same class as 1.6c findings.

## Expectations by layer (bound to the DECLARED layer, before interpretation)

- **persistent**: verbatim recall expected; deviation = degradation signal.
- **session**: noise/imperfection within one session is expected behavior,
  NOT degradation. Do not raise alerts on session-scoped drift.
- **transient**: exact answer is a bonus, never evidence — accuracy of a
  transient layer cannot certify memory health (absence-of-guarantee
  is not presence-of-guarantee).
- Invariant: applying one layer's expectations to another layer's answer
  is a reading error (false RED / false GREEN alike).

## Unknown handling (fail-closed and loud)

`unknown` → suspend judgment: NO degradation verdict AND NO success verdict
(abstention, counted toward the abstention metric — cf. verification_suite).
Conservative mode + explicit loud diagnostic event (LOG-3.4), non-blocking
(precedent: [REC] two-level verdict, 1.6c). The layer MUST NOT be guessed
to unblock interpretation.

## Orthogonality (three axes, no dual ownership)

- **layer** = lifetime CLASS (named enum) — I15, interpretation axis.
- **scope** = grouping BOUNDARY (scope_enum) — pool/ownership axis.
- **retention** = storage DURATION (parameter) — §2.2, time axis.
Layer is a read-only diagnostic label: owns no storage, sets no policy.
Anti-confusion: scope "local-session" (access boundary) ≠ layer "session"
(source context); layer(transient) vs short retention both "about short" —
divorced by kind (named class vs number; class is never derived from
duration and vice versa). I15 REFERENCES §2.2 where lifetime is defined,
never duplicates canon.

## v0.2 candidates

- Heuristic layer assignment with declared confidence (deferred: inference
  without source is RED in v0.1, cf. Yasha auto-levels precedent 1.5).
- Tumbling review of zone expectations; semantic adequacy of expectations.

## v0.2 boundary

Undecided here moves to backlog v2.1 and MUST NOT block the v0.2 build.

## CLI integration point (documented, not implemented)

`audit layers` subcommand after v0.2 canonization (precedent 1.5).
CLI 1.4 and gates 1.1–1.6c untouched by package 1.6d.
