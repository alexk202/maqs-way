Canonized in da40be8 (SPEC §3.4, v0.3). This file is the historical formulation; the normative text is in SPEC.

# I14 Handler Registry Formulation (v0.1, NOT canon)

> Status: formulation proposal, package 1.6c. NOT normative until
> canonization (target v0.3) with owner signature. I14 is a known gap
> (owner: 1.6c-formulation, closes_in: v0.2 canonization).
> Core thesis: detection without reaction ≠ coverage.

## Registry semantics (handler ≠ path, both allowed)

A probed class MUST have a reaction: handler AND/OR path (at least one).
- **handler** — local reaction (own-process side, as Halt in 1.6a).
- **escalation-path** — owner/operator notification with degraded continuation
  (external side, as Escalate in 1.6a). A path MUST terminate at a declared
  recipient (owner/operator); path-into-void = uncovered (same class as
  halt-without-alert, B5-family).
- Both simultaneously is LEGAL (handler + fallback-path = defense in depth).
  XOR-forbidding is rejected: it would outlaw a standard pattern without
  a canon source. Dictionary inherited from 1.6a, not redefined
  (Halt : Escalate :: handler : path). Counter classes from 1.6a, when
  listed here, carry reaction = counter (aggregate/halt/escalate):
  1.6a defines, 1.6c references — no double ownership.

## Catalog (closed list, honest boundary)

The class catalog is a DECLARED synthetic list; completeness is NOT claimed
("checked N declared classes; completeness NOT claimed" is a mandatory
report line). Growth rule (precedent: MAQS-whitelist 740c304): extension
happens by commit only, never silently at runtime; each new class enters
with source (incident/audit) and owner. Future rules in new entries MUST
use namespaced form (not bare) — lesson 1.6b.

## Verdict model (two levels, not a choice)

- **Probe level (unit):** orphan class → RED. A check that cannot fail is
  not a check. Inconsistency inside the declared catalog is STRICT.
- **Gate level (integration):** [REC]-findings are reported-not-failing:
  the aggregate gate is not blocked, but findings MUST be NAMED in the
  report (never folded). [REC] governs BLOCKING, not verdict-ability.
  "0 findings" and "check not run" are distinguished states.
- Coverage metric: handled/probed; every orphan listed by name.
- Advisory flag: I14 [REC] status is carried in the REPORT, not in gate
  semantics (precedent: known-gaps-with-owners, 1.1–1.5).

## v0.2 candidates

- The reviewer's owners_registry/sla/fallback schema for paths (deferred: no canon
  source for sla scales in v0.1).
- Tumbling catalog review; exception taxonomy import.

## v0.2 boundary

Undecided here moves to backlog v2.1 and MUST NOT block the v0.2 build.

## CLI integration point (documented, not implemented)

`audit handlers` subcommand after v0.2 canonization (precedent 1.5).
CLI 1.4 and gates 1.1–1.6b untouched by package 1.6c.
