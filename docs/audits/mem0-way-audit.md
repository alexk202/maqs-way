# Way-audit of Mem0 OSS (MAQS-Way v0.2 application example)

> Status: draft audit example, NOT part of the canon. Tone — help, not a roast.
> Method: static code reading (no execution, no infra).
> Audited code: `mem0ai/mem0` @ `0724291` (2026-10-14), shallow clone.
> Auditor: MAQS-Way v0.2 (principles P1–P8 + write integrity B1–B6).
> Rule: only facts from code/docs, with paths; whatever was not verified is stated as such.

## Summary

| Way property | Verdict | One line |
|---|---|---|
| P4 Isolation | STATIC IMPLEMENTATION EVIDENCE; BEHAVIORAL VERIFICATION PENDING | Tenant filters before top-k, keys unspoofable via metadata |
| P2 Provenance | PARTIAL | Actor/role in history; no source ref, policy, or confidence on the record |
| P3 Aging | PARTIAL | Opt-in expiration exists; decay is platform-only, not OSS |
| P5 Deletability | PARTIAL | Delete clears the vector + writes history; history stays queryable, no tombstone |
| B Write integrity | PARTIAL | App-level md5 dedup, no UNIQUE constraints or transactions; silent paths exist |
| P1 Veracity | GAP | No model_output typing / trust ceiling on summarization |
| P8 Measurability | GAP (in-tree) | `evaluation/` is an empty submodule, harness not vendored |
| Logging (§3.4-like) | PARTIAL | Closest to an audit trail is SQLite history; no structured sink |

> P4: reclassified to "static implementation evidence; behavioral
> verification pending" (see "Done well", item 1).

## Done well (worth crediting)

1. **Isolation (P4) — exemplary.** `mem0/memory/main.py:1471-1475` — `search/get_all`
   require a tenant filter (`user_id|agent_id|run_id`), else `ValueError`;
   filters go into the vector store `query_filter` before top-k
   (`qdrant.py:428-434`, over-fetch `max(limit*4,60)`); key spoofing via
   `metadata` is cut off by `_strip_identity_keys()` (`main.py:138-162`).

   Status reclassified following external reviewer feedback
   (E. Mnemoverse, private correspondence, 2026-10). Static
   evidence remains valid and credited: tenant filter logic
   and identity-key stripping are present in the reviewed
   code paths. However, the audit executed nothing (see
   Method and Limitations); therefore no runtime results
   exist for: (1) independently authenticated callers,
   (2) wrong or omitted scope, (3) writes under read-only
   credentials, (4) access after revocation. These four
   case classes constitute the pending behavioral
   verification scope. The original COVERED label
   implied behavioral proof that was not performed —
   marking error of the audit, not a finding against
   the audited implementation.
2. **History as audit trail.** SQLite `history` (`storage.py:150-191`) keeps
   `old/new_memory, event, actor_id, role, is_deleted` — mutation provenance is
   traceable, `created_at` survives update (`main.py:2072-2080`).
3. **Opt-in expiration.** `expiration_date + _payload_is_expired()`
   (`main.py:427-451`) — a TTL mechanism exists, even if hiding rather than purging.

## Gaps with specifics (what to improve, per file)

1. **P1 — type model output.** LLM-extracted facts are written as
   `payload["data"]` directly (`main.py:1031-1034`); the procedural requirement
   "record every agent output verbatim" (`configs/prompts.py:327,352`) has
   no trust ceiling. Suggestion: a `source.type` field + confidence ceiling
   until external confirmation (MAQS F8 pattern).
2. **P2 — source ref + confidence on the record.** `MemoryItem`
   (`configs/base.py:16-26`) carries no source ref/URL, policy/version, or
   confidence. History partly covers this, but the record itself does not.
3. **P5 — history residue.** A deleted record stays queryable via `history()`
   (`storage.py:227-255`); no vector tombstone, no cache purge. For strict
   GDPR posture, a cascade + governance tombstone is needed (Way P5 pattern).
4. **B — atomicity and silence.** `vector_store.insert` followed by
   `batch_add_history` in separate `try` blocks (`main.py:1056-1098`): partial
   writes are possible. Silent paths: JSON parse error → `return []`
   (`984-991`); entity upsert swallowed into warning/debug (`649-663`).
   Suggestion: outbox/compensation + metrics on every silent path (B5).
5. **P3 — decay is platform-only** (`client/project.py:400-412`, search-time
   ranking); OSS `notices.py:134` states plainly it is unsupported. An honest
   product boundary — but OSS users get no decay at all.

## Honest boundaries of this audit

- Nothing was executed: runtime behavior, real vector residue, metrics —
  not verified (that needs a bench, not reading).
- Platform code (decay, linked_memory_ids) is only partly visible — verdicts
  cover OSS only.
- Benchmarks live in an external submodule repo, not initialized: no claims
  about its contents.

## Next steps

- Show the report to Mem0 authors via issue, give them time to respond (plan, step 4).
- Their corrections/responses go in as a second commit to this file, findings are not rewritten.

## Changelog

- 2026-10-23: P4 reclassified
  from COVERED to "static implementation
  evidence; behavioral verification pending" following
  external reviewer feedback. No other verdicts changed.
  Reviewer's label adopted verbatim and queued for the
  MAQS glossary.
