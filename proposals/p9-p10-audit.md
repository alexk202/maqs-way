# P9/P10 Audit Procedure Formulation (v0.1, NOT canon)

> Status: formulation proposal, package 1.7a. NOT normative until
> canonization (target v0.3) with owner signature. P9/P10 are known gaps
> (owner: 1.7a-formulation, closes_in: v0.2 canonization).
> One-sidedness is DECLARED UPFRONT here, not implied: every P9 run
> reports "negative = inconclusive; coverage NOT claimed".

## P9 — Controlled artifact experiment (one-sided)

Canary/decoy/echo probes (MAQS P9-a/b/c). Evaluation is one-sided:
- positive (probe fires: canary retrieved / decoy mentioned / echo appears)
  = PROOF of the tested property.
- negative (probe not found) = INCONCLUSIVE — never pass, never "clean",
  only "not tested by this run". A silent canary proves nothing about
  the threat — only about the canary.
- Mixing a one-sided run with coverage = RED (the P9 run would become
  the 1.6c level-substitution: "not detected" issued as "clean").

## P10 — External auditor isolation (read-only, verified by fact)

The auditor is read-only. Read-only is a DECLARED property, confirmed by
fact, not by promise. Procedure: snapshot the tree → run all gates →
verify. Verification MUST include untracked files (`git status --porcelain`,
not tracked-only): creating a new file IS a write even if tracked files
are untouched — otherwise false-safe. A gate that writes into the repo
(modification OR new file) fails P10. Write access for the auditor is
out of scope (SUPP-EXT-01) — an honest boundary, not a defect.

## v0.2 candidates

- Golden canary corpus; decoy-generation procedure.
- Auditor certification checklist.

## v0.2 boundary

Undecided here moves to backlog v2.1 and MUST NOT block the v0.2 build.

## CLI integration point (documented, not implemented)

`audit procedure` subcommand after v0.2 canonization (precedent 1.5).
CLI 1.4 and gates 1.1–1.6d untouched by package 1.7a.
