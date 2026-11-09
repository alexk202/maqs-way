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

Earlier same-day runs of 2026-10-26 (`02e1c4c`, `d5e48dc`) and what the verified
label rests on are recorded in the changelog of
[`docs/audits/mem0-way-audit.md`](../../docs/audits/mem0-way-audit.md).