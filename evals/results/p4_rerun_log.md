# P4 isolation — run log (append-only)

The verdict artifact `p4_mem0_isolation_report.json` holds the latest run; each
run overwrote it, so this file lists every run with the commit that carries its
artifact version. Retrieve any earlier version with
`git show <commit>:evals/results/p4_mem0_isolation_report.json`.

All three runs: `config_sha256 548343f61ef4…`, verdict PASSED, same stand class
(CPU-only, stub embedder, stub chat, `infer=False`), Python 3.12.2.

| # | Run date (UTC) | Artifact commit | Kernel | mem0 install | Verdict |
|---|---|---|---|---|---|
| 1 | 2026-10-26T09:50:24Z | `93787c9` | 7.0.0-38-generic | `file:///home/aleksandr/Projects/mem0-pilot` | PASSED |
| 2 | 2026-11-09T11:21:00Z | `978ceae` | 7.0.0-42-generic | `git+https://github.com/mem0ai/mem0@0724291bd864cf807e88ee8981c8226644e8fb42` | PASSED |
| 3 | 2026-11-09T11:33:59Z | `08622da` | 7.0.0-42-generic | `git+https://github.com/mem0ai/mem0@0724291bd864cf807e88ee8981c8226644e8fb42` | PASSED |

Run 1 is the verdict run cited across the repo and the version carried by tag
v0.3. Runs 2 and 3 are independent reproductions on a later kernel with mem0
installed from the pinned commit instead of a local path; run 3 was built in a
fresh venv (see the commit messages of `978ceae` and `08622da`). Between run 1
and run 2 the only artifact fields that changed were `provenance.date`,
`observed_behavior.foreign_memory_id` (a per-run UUID), `environment.uname` and
`environment.pip_freeze_mem0`; every verdict, counter and control is identical.

## Container reproductions

Runs below were produced by `repro/` (Python 3.12.2, pinned base image digest,
no network, no provider keys). Their artifacts are reproduction checks, not new
verdicts, and are not committed: what is recorded is the comparison against the
run-1 artifact.

| # | Date (UTC) | Image digest | config_sha256 match | main/controls match | Wall clock |
|---|---|---|---|---|---|
| C1 | 2026-11-10T14:48:02Z | `sha256:5dc6f84b5e97bfb0c90abfb7c55f3cacc2cb6687c8f920b64a833a2219875997` | yes | yes | 3 s |
| C2 | 2026-11-10T14:48:10Z | `sha256:5dc6f84b5e97bfb0c90abfb7c55f3cacc2cb6687c8f920b64a833a2219875997` | yes | yes | 2 s |

Note on a field that reads oddly: `provenance.config_effective.mem0_version` is
`v1.1`, which is mem0's own config `version` field (described upstream as "the
version of the API"), not the package version. The package at the pinned commit
`0724291b` is mem0ai 2.2.1, as `environment.pip_freeze_mem0` shows. The key name
is part of the config fingerprint, so it is left as is; renaming it would change
`config_sha256` and break comparability with runs 1-3.

Earlier same-day runs of 2026-10-26 (`02e1c4c`, `d5e48dc`) and what the verified
label rests on are recorded in the changelog of
[`docs/audits/mem0-way-audit.md`](../../docs/audits/mem0-way-audit.md).