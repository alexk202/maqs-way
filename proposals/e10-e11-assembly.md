# E10/E11 Assembly Formulation (v0.1, NOT canon)

> Status: formulation proposal, package 1.5. This document is NOT normative:
> E10/E11 MUST NOT be cited as operative Way rules until canonization (target v0.3)
> with owner signature. In coverage fixtures both items are known gaps
> (owner: 1.5-formulation, closes_in: v0.3 canonization).
> MAQS 1.8.1 extensions not yet reflected: none → v0.4.
> Sanction: owner decision on v2 final (pending at build time).

## Glossary (frozen for v0.1-formulation; redefinition only via separate sanction)

- **alive / protected**: `alive: bool` flag on a record — declared, not inferred.
- **alive_cap**: max protected records within one scope for one subject (advisory, [REC]).
- **cap_overflow**: event emitted when a protect request exceeds the cap.
- **critical**: explicit label with provenance (owner or authorized process) — declared, not inferred.
- **unlabeled_ratio**: share of records/blocks without a critical mark — reported, not gated (v0.1).
- **positioning** (E11 sense, sanction 1.5): placement procedure for critical blocks
  (head/tail zones + positional audit). NOT the bare word in SPEC §2.4.
- **head / tail zones**: first / last 15% of assembled context tokens (v0.1 default).

## E10.cap — Alive memory cap (MAQS E10 [REC], indicative)

The alive cap is per-scope-per-subject (cap applies within each memory scope
for each subject independently, not globally). Scope anchor: `scope_enum`
in `maqs-way-standard.json` (local-session, agent-private, user-portable,
team-shared, org-shared).

Effect: `alive: true` exempts the record from decay and summarization while
the flag is set. Non-effect: does NOT block delete (delete is governed by
`legal_hold`, see below).

Overflow (default): new protection is DENIED (fail-closed for protection);
the event is logged as `cap_overflow {subject, scope, cap, attempted_id}`;
N consecutive denials escalate to the owner (advisory, since E10 is [REC]).
The system MUST NOT silently revoke existing protections and MUST NOT
silently reject new ones. Rationale: default-FIFO eviction leaves
`alive: true` set while protection is actually gone — declaration outlives
fact (silent-fail, class B5). A lying flag is worse than forgetfulness.

Overflow (opt-in only): `overflow: evict_oldest` — explicit configuration per
system; each eviction event MUST be logged with record id and reason
(no silence even opt-in). Opt-in explicitly redefines `alive` semantics
(policy priority, not absolute protection) and therefore is not a lie.

Cap violations are measurable (`alive_cap_overflow_rate`, P8 pattern) but
non-blocking in v0.1-formulation.

## E10.alive_vs_hold — Orthogonal mechanisms

`legal_hold` and `alive` are orthogonal mechanisms: `legal_hold` blocks
deletion (governance-level, hard); `alive` protects against decay and
summarization (significance-level, [REC]). A record may carry both flags
simultaneously; neither implies the other. Hold does not grant
alive-protection and vice versa; removing one flag never removes the other.
Check: `is_forgettable(r) = not r.alive and not r.legal_hold`.

## E11.critical — Declared critical labels (MAQS E11 [IMP])

Critical status is an explicit label with provenance (source: owner or
authorized process). No automatic importance inference in v0.1: `importance`
in canon is an F8 ceiling (a restriction), not a model field — no scale,
no thresholds, no source. Unlabeled records are treated as non-critical
(no reordering, no guessing); `unlabeled_ratio` is measured to keep the gap
visible. Unmarked blocks produce an explicit log ("0 critical blocks"),
never a silent pass-with-guessing.

`E11.verify_placement(context)` is a structural audit (no LLM): every
critical-labeled block MUST occupy head or tail zones; middle-zone critical
placement = FAIL. Semantic adequacy of zone sizes — v0.2.

## E11.status — Known gap (anchored, not partial)

The word "positioning" in SPEC §2.4 names the topic; it sets no norm
(no subject/predicate/condition: no rule, no critical definition, no
verification procedure required by MAQS E11 [IMP], Liu et al.,
lost-in-the-middle). Word-as-rule mapping is rejected (rule #5).
Anchor: SPEC §2.4. Formulation lives here; closes_in: v0.3 canonization
(owner signature). E10 status: same bridge (formulation here, canonization v0.3).

## v0.2 candidates (NOT rejected, awaiting source — do not act on in v0.1)

- The reviewer's 3-level critical scheme (provenance → importance ≥ 0.85 → type list;
  WARN on importance ≥ 0.75 unlabeled). Activation condition: `importance`
  becomes a real model field with defined scale (requires canon change,
  owner signature). Revision: with v0.3 canonization.
- General pin mechanism "vector field == canon path" (from 1.4): criterion ≥ 3 pins.

## v0.2 boundary

Everything not included in round-2 convergence moves to backlog v2.1 and
MUST NOT block the v0.2 build. Moratorium: no edits to SPEC §2.4 wording or
this proposal before v0.2 release except direct contradictions with sanction 1.5.

## Precedent line (for v0.2 reviewers)

FIFO = opt-in only (precedent: B5 silent-fail). Auto-importance = blocked
until threshold canonization (precedent: 0.8 drift, package 1.3).
Beautiful numbers/labels without a canon source stay beautiful — and out.

## Change log

- v0.1 (package 1.5): rule #5 applied symmetrically — to FIFO default and to
  auto-importance thresholds alike, including against their own authors
  (second precedent after 0.3/0.8; pattern: "a beautiful number without a
  source is still a number by eye").
- Council protocol adopted: opinion + recommendations + exact changes +
  hold-list + justified comments on committed work only.

## CLI integration point (documented, not implemented)

Migration of this gate into `audit` (e.g. `assembly` subcommand) = separate
package after v0.3 canonization, if the formulation survives review
(precedent: pin mechanism, package 1.4). CLI 1.4 untouched by package 1.5.
