# Core-reference policy: when `maqs_core_reference` moves

Status: policy note, outside the canon. No owner signature required to
change this file; changing what it governs does require one.

## Rule

`maqs_core_reference` in `maqs-way-standard.json` — the single source that
gate G8 holds every MAQS version mention to — follows MAQS **minor**
versions only.

- A MAQS minor release (1.9 → 1.10) moves the reference. It is a canon
  change: owner signature on the canon file hashes, recorded in SPEC §7.
- A MAQS patch release (1.9.1, 1.10.1) does **not** move the reference.
  It is recorded as one line in the companion repo's sync log
  (`maqs-way-evidence/README.md`) and nowhere else.

## Why

A MAQS patch release, by its own definition, leaves the item set, the
criticality markers and the pass/fail logic unchanged — an audit run
against the preceding minor stays valid. Way's claim "MAQS vX.Y remains
audit core" therefore stays true across patches, and moving the reference
would cost a signed canon commit and a release stamp for a statement that
did not change.

Precedent: MAQS 1.9 → 1.9.1 (2026-11-11) left the reference at v1.9;
MAQS 1.10 → 1.10.1 (2026-11-18) left it at v1.10.

## The exception, stated so it is not argued case by case

If a patch release touches any of the three — the item set, the markers,
or the verdict logic — it is treated as a minor for this purpose: the
reference moves, with a signature, whatever the version number says. The
version number is not the test; the three invariants are.

## What this does not cover

Way's own release stamps (SPEC/RU headers, JSON `version`,
`spec-manifest`, `scoreboard`, `CITATION.cff`) are governed by G0 and the
release checklist, not by this note. Cross-repo version mentions in
`maqs-way-evidence` are checked by hand at each release: that repo has no
gate of its own, and `.githooks/name_guard.py` there imports its pattern
from this canon but checks names, not versions.
