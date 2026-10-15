# 0.5a/0.6a Pipeline Hygiene Formulation (v0.1, NOT canon)

> Status: formulation proposal, package 1.7b. NOT normative until v0.2
> canonization with owner signature. 0.5a/0.6a are known gaps
> (owner: 1.7b-formulation, closes_in: v0.2 canonization).

## 0.5a — Dead code [CRIT]

Green tests on code never invoked by the running system are a false
safety signal. Rule: every `schemas/check_*.py` MUST be either
(a) invoked from `maqs_way_audit.py`, or
(b) listed in DECLARED_STANDALONE with a documented integration point.

DECLARED_STANDALONE (v0.1, closed list — extension by package, not silently):
check_e_assembly (1.5), check_i13_redaction (1.6b), check_i_counters (1.6a),
check_i_handlers (1.6c), check_i_layers (1.6d), check_audit_procedure (1.7a).
Integration points documented in respective proposals/scripts; CLI aggregation
of standalone gates = candidate for 1.8. Uninvoked AND undocumented = dead → RED.
Self-hosting applies: this gate scans its own repo, including itself
(check_pipeline_hygiene is invoked from no CLI — it carries its documented
point here and runs on watch; if unwired and unpointed, it flags itself).

## 0.6a — Local baselines [IMP]

Per store/context own baseline (file counts, vector counts, sizes).
Baseline file `schemas/baseline.json`: namespaced counters + provenance
(commit + date of recording) + declared tolerance (default ±10% per counter;
tolerance changes are declared, owner-signed — rule #5 class counters).
Drift beyond tolerance → FLAG (advisory, visible, accumulated), not RED:
no canon threshold exists, and RED-on-growth would punish legitimate work.
RED only for: baseline missing/corrupt, or counter removed from tracking
without explanation. Baseline changes only with the commit that explains
the drift (Stasik rule).

## v0.2 candidates

- Golden canary corpus for P9; auditor certification checklist (1.7a).
- Canonical drift tolerances per store.

## v0.2 boundary

Undecided here moves to backlog v2.1 and MUST NOT block the v0.2 build.

## CLI integration point (documented, not implemented)

`audit hygiene` subcommand after v0.2 canonization (precedent 1.5).
CLI 1.4 and gates 1.1–1.7a untouched by package 1.7b.
