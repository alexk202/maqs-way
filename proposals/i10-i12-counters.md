# I10/I11/I12 Counter Formulation (v0.1, NOT canon)

> Status: formulation proposal, package 1.6a. NOT normative until v0.2
> canonization with owner signature. In coverage fixtures all three items
> are known gaps (owner: 1.6a-formulation, closes_in: v0.2 canonization).
> The C8→I11 bridge lands here as CONSOLIDATION (subject moved to I11),
> not closure: I11 stays a gap.

## Policy triple (rule #5, class counters)

Every counter declares THREE independent literals (never glued):
threshold N, window {type, size}, action. Threshold and window are
independently tunable (precedent: the council two-literal lesson).
Window types: sliding (events within trailing size) | tumbling (fixed
buckets). Every counter declares its equality-key field (signature):
without a key, "identical" is undefined and the counter is
nondeterministic — rejected.

## I10 — Noise budget (MAQS I10 [IMP])

- threshold: 3, window: {sliding, 5m}, key: warning text.
- action: aggregate with counter (N identical warnings → one record + count),
  never emit individually past threshold.
- B5-link: claimed-success-without-performed-work is a B5-failure, detected
  as a pure function of (claimed_events, performed_actions) over a DECLARED
  work-sink (recorded side-effects). Claimed success + empty sink → RED.
  I10 exists to prevent duplicate noise from masking false success.

## I11 — Recovery loop (MAQS I11 [CRIT])

- threshold: 3, window: {sliding, 10m}, key: exit code.
- action: halt + alert. Halt stops OWN process; halt-without-alert is
  forbidden exactly like restart-without-diagnosis.
- Alert sink is a REAL persistent store (journal file / syslog), never
  bare stderr/exit code: stderr does not survive halt, exit code is visible
  to the parent only. An alert that cannot be read after halt is a
  silent-fail (class B5). Probe reads the trace AFTER halt from the file.

## I12 — Escalation budget (MAQS I12 [CRIT])

- threshold: 3, window: {sliding, 1h}, key: dependency + error code.
- action: escalate (alert/halt/flagged degradation), never busy-poll.
  Escalate targets EXTERNAL dependencies (no right to stop, voice only)
  and is REPEATABLE on a schedule — a notification contract, not a one-shot
  shout and never a busy poll. Escalate-without-journal-entry = B5-failure
  (same class as halt-without-alert).
- Adjacent, not covering: SPEC §2.3 (appeal-escalation + operator SLA) shares
  vocabulary only (different trigger, different mechanism). Closing this gap
  with "already in §2.3" words is rejected in advance.

## Halt ←→ Escalate boundary

Halt applies to own process (right to stop = obligation to alert).
Escalate applies to external dependencies (no right to stop, voice only).
On conflict (both conditions met): HALT dominates (safety) + escalate owner.
`flagged degradation` MUST be observable in the sink, else degradation is
silent = B5.

## v0.2 candidates

- Tumbling-window deployments (declared per deployment; sliding is v0.1 default).
- Per-scope/per-subject counter partitioning (cf. E10 cap semantics, 1.5).

## v0.2 boundary

Undecided here moves to backlog v2.1 and MUST NOT block the v0.2 build.

## CLI integration point (documented, not implemented)

`audit counters` subcommand after v0.2 canonization (precedent 1.5).
CLI 1.4 and gates 1.1–1.5 untouched by package 1.6a.
