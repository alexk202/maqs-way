# MAQS-Way — Common Path from Policies to Implementation

**Status:** v0.2.1 — evidence release (canon unchanged from v0.2; open known gaps listed in SPEC §7)
**Core:** MAQS v1.8.1 remains audit core: https://github.com/alexk202/memory-architecture-standard

> **Formula:** MAQS = practical audit of architecture and typical failures (how to verify)
> Way = common model + measurable criteria + lifecycle + reproducible verification (how to build)

MAQS checks that mechanism exists. Way proves it works.

---

## Why Way?

- **Policy layer** is overcrowded: GDPR Art17, EU AI Act Art12/13/19, RBAC, governance docs
- **Audit layer** exists: MAQS v1.8.1 — rare checklist backed by 20k+ tracebacks and production incidents
- **Path layer** was missing: which tools, patterns, schemas to implement policy in memory architecture and how to prove it

Without path, policies are written by lawyers, audits are done ad-hoc by engineers.

## What Way adopts (not competes)

| Family | What it provides | How Way uses it |
|---|---|---|
| OMPS `rdh073/omps` | Vendor-neutral portability `memory-item.schema.json` | Canonical structural contract |
| AMSP `sanej/amsp` | Lifecycle + scope model `active→deleted`, `user-portable` etc | Scope + state machine |
| OAMP `deep-thinking-lab` | Provenance mandatory `agent_id` binding §4.3 | Provenance as requirement |
| Zep/Graphiti `getzep/graphiti` | Bitemporal `valid_at/invalid_at + t_created/t_expired` | Lifecycle + invalidation |
| Tombstone `poojan6216/tombstone` | Physical deletion verification 92-100% residue bench | Deletion lattice |
| LoCoMo/LongMemEval/MemoryAgentBench | Measurable quality R@k, temporal, abstention | Golden sets |
| OWASP Agentic ASI06 | Memory poisoning tests | Security verification |
| EU AI Act Art12 + OTel GenAI | Logging by design | Observability |

## Three layers

**1. Principles** — 8 immutable: Veracity, Provenance, Controlled Aging, Isolation, Deletability, Recoverability, Portability, Measurability

**2. Architecture** — Data model (OMPS + OAMP), lifecycle `ACTIVE→STALE→CONTESTED→SUPERSEDED→EXPIRED→ARCHIVED→DELETED→TOMBSTONE→COMPACTION`, bitemporal with temporal priority (`invalid_at < now` → `EXPIRED`, not `SUPERSEDED`), 6-tier deletion cascade `graph_edges → nodes_if_sole_provenance → embeddings_fk → facts_fk → artifacts → rounds`, Content-as-Data fenced `<retrieved_context>`, `visible_to` semantic masking

**3. Verification** — Property / Verification / Example separated. Golden sets + metrics CI gate / target: R@5 ≥0.7 / ≥0.85, temporal ≥0.65 / ≥0.8, abstention ≥0.8 / ≥0.9, duplicate ≤5% / ≤2%, contamination ≤1% / 0, residue 0. Deletion lattice LOGICAL/PHYSICAL/SEMANTIC/MODEL. EU AI Act logging + OTel with allowed/forbidden keys. Canon: `maqs-way-standard.json` → `verification_suite.metrics`.

## Repo structure

```
SPEC.md — main spec v0.2.1 EN
SPEC-RU.md — RU version v0.2.1
maqs-way-standard.json — machine-readable v0.2.1 (8 principles P1-P8)
conformance/ — valid/invalid vectors + manifest.json
evals/ — how to run LoCoMo/LongMemEval
docs/ — mapping to MAQS, landscape, outreach drafts, articles
proposals/ — v0.1 roadmap snapshot (historical)
```

## Companion artifacts

Self-audit evaluator, cheatsheets (P1–P8 + worked patterns), wired RED self-tests, GitHub Action template:
https://github.com/alexk202/maqs-way-evidence — derived from canon, nothing there rewrites it.

## Relation to MAQS

- MAQS v1.8.1 = audit checklist you put on table, CRIT/IMP/REC verdict, backed by incidents
- Way = governance contract that references MAQS sections 0-J as implementation evidence

Two repos, one coordinate system. MAQS stays clean.

## Quick start

```bash
# inspect the machine-readable standard (valid JSON)
python -m json.tool maqs-way-standard.json
# conformance corpus (expected verdicts + rule_ids)
cat conformance/manifest.json
```

> Audit CLI v0.1 ships (`schemas/maqs_way_audit.py`: schema + manifest + lint + coverage, namespaces, canon-pin) — run `python3 schemas/maqs_way_audit.py all`. `data_model.$ref` is active (`schemas/memory-item.schema.json` landed, gate green). Executable behavioral harness — planned, v0.3 (see SPEC §6 Backlog). `schema_version` (`omps-0.1.0+way-v0.1.3`) pins the data model, not the release (v0.2.1): the model is frozen since v0.1.3, the release grows — by design.

See `docs/articles/devto-draft.md` for the first DevTo article (v0.1.4).
v0.2 article (live): https://dev.to/aleksandr_kossarev_e23623/maqs-way-v02-shipping-a-standard-with-open-gaps-and-naming-them-5cef
Worked audit examples: [Mem0](docs/audits/mem0-way-audit.md) · [Graphiti](docs/audits/graphiti-way-audit.md) · [Letta](docs/audits/letta-way-audit.md).

> Check not that the mechanism exists. Check that it works.
