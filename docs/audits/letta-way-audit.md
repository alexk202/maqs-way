# Way-audit of Letta MemFS client (MAQS-Way v0.2 application example)

> Status: draft audit example, NOT part of the canon. Tone — help, not a roast.
> Method: static code reading (no execution, no infra).
> Audited code: `letta-ai/letta-code` @ `cc4654a` (2026-10-14), shallow clone.
> Auditor: MAQS-Way v0.2 (principles P1–P8 + write integrity B1–B6).
> Rule: only facts from code/docs, with paths; whatever was not verified is stated as such.

## Scope boundary (read first)

This repo is the **MemFS client/harness**, not the Letta server: local memory is
git-backed Markdown under `~/.letta/agents/{id}/memory/`, synced to Letta Cloud.
The server-side archival/recall store (blocks, passages, embeddings) is closed —
only its client shadow is visible here. **All verdicts below cover the client.**
Server behavior is explicitly out of scope, not implicitly condemned.

## Summary (client scope)

| Way property | Verdict | One line |
|---|---|---|
| P4 Isolation | COVERED (client-side) | Per-agent roots, symlink-resolved containment, fail-closed writes |
| P8 Measurability | COVERED (policy-heavy) | Deep unit/hook/e2e suites; no memory-quality benchmarks found |
| P2 Provenance | PARTIAL | Git commits carry agent author; file bodies carry no source/confidence |
| P1 Veracity | PARTIAL | Structural gates + read_only protection; no trust levels on content |
| P5 Deletability | PARTIAL | No hard-delete API; residue = git history by design |
| B Write integrity | PARTIAL | Idempotent no-op commits, deduped pathspecs; lock bypass + quiet fallbacks |
| P3 Aging | GAP | Budgets only (sizes/depth); no TTL/expiry/decay/supersede fields |
| Logging | PARTIAL | Debug traces + push log; no structured memory audit ledger |

## Done well (worth crediting)

1. **Isolation (P4) — fail-closed by construction.** Per-agent roots
   (`memory-filesystem.ts:46-57`); `resolveAllowedMemoryRoots()` +
   `isOwnMemoryWrite()` allow writes only inside the own checkout,
   symlink-resolved, default-deny (`memory-paths.ts:181-208`,
   `memory-write-allowance.ts:37-61`); subagent sandbox can write its own
   memory but not others' (`memory-confinement.ts:13-21`); `..`, hidden and
   absolute paths rejected with realpath containment (`memory.ts:371-397`).
2. **Self-edit guards (P1-half).** `read_only` frontmatter cannot be
   added/changed/removed by the agent; `HEAD read_only:true` files wholly
   unmodifiable (`memory-frontmatter.ts:55-61,91-120`); `.memfs.config.json`
   changes need human approval (`memory-constraints.ts:142-146`).
3. **Idempotent commits (B-half).** `commitMemoryPaths()` stages, checks
   `hasStagedMemoryChanges()`, else returns `{committed:false}`
   (`memory-git.ts:1184-1195`); delete of a missing file is a no-op success
   (`commands/memory.ts:1001-1023`); pathspecs Set-deduped (`1039-1043`).
4. **Policy test depth (P8-half).** Frontmatter, constraints, filesystem,
   permissions, hooks, conflict-repair, ordering and e2e suites
   (`bun test` + `scripts/check.js`) — the strongest *policy* verification
   among audited systems; memory-quality benchmarks (truthfulness, aging)
   are the missing half.

## Gaps with specifics (what to improve, per file)

1. **P3 — no aging at all.** No TTL/expiry/decay/supersede fields anywhere
   (`memory-constraints.ts:302-308` has budgets only: sizes, depth).
   Contradiction handling is Git-level (merge/rebase claims,
   `memory-conflict-repair.ts:24-45`); semantic supersession policy: none found.
   Suggestion: `expires_at`/`supersedes` fields + a reaper, even a dumb one.
2. **P2 — bodies without provenance.** Git log carries author/date, but file
   bodies carry no source ref or confidence (`memory-frontmatter.ts:64-66`:
   only `name/description`). Suggestion: frontmatter `source:` + `confidence:`.
3. **P1 — untyped free Markdown.** Agent-written memory has structural gates
   only (frontmatter present, known keys, size/depth). Suggestion: content
   typing or trust ceiling for agent-derived facts (MAQS F8 pattern).
4. **P5 — git history as residue.** No tombstone API; deleted content persists
   in history, remotes and `memory-repository-push.log`. If that is by design
   (recoverability-first), state it; if GDPR-style purge is ever needed, a
   hard-purge path with tombstone is missing.
5. **B — lock bypass + quiet fallbacks.** Primary-agent edits bypass the
   file-lease (`memory-operation.ts:25-44`, degrading to Git conflicts);
   `catch {}` fallbacks on unstage, author-name, secrets init
   (`1227-1231`, `commands/memory.ts:1039-1041`, `memory-filesystem.ts:605-609`);
   push await capped at 8s then backgrounded. Suggestion: metrics on every
   fallback path (B5) + lease coverage for primary edits.
6. **Logging — no ledger.** `debugLog` traces + push-failure log are
   diagnostics, not an audit trail. The de-facto trail (git history +
   `write_memory_file_response {committed, commit_sha}`) works but is implicit.

## Honest boundaries of this audit

- Nothing was executed; server-side archival/recall memory is closed and
  unjudged — a "gap" here means "absent client-side", never "absent at Letta".
- Recall-aging and semantic-conflict behavior were not found client-side;
  they may live server-side.
- No comparison ranking with the Mem0/Graphiti audits is attempted.

## Next steps

- Show the report to Letta authors via issue, give them time to respond.
- Their corrections/responses go in as a second commit to this file, findings are not rewritten.
