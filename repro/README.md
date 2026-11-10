# repro/ — P4 in one command (container)

Reproduces the P4 mem0 isolation run (`evals/p4_mem0_isolation.py`) in a pinned
container, without provider keys and without network access at run time. The
image carries its own copy of `evals/`; the host repository is never mounted,
so nothing in the working tree — including
`evals/results/p4_mem0_isolation_report.json` — is written to.

## Build (once; needs network)

The build downloads the pinned base image (`python:3.12.2-slim` by digest) and
installs `requirements.txt`, including the `git+https` pin of mem0 at commit
`0724291b`. **Network is required for this step only.** Build from the
repository root (`requirements.txt` and `evals/` are the build context):

```bash
podman build -f repro/Dockerfile -t maqs-way-p4:local .
```

With Docker the syntax is the same (`docker build -f repro/Dockerfile -t
maqs-way-p4:local .`).

## Run (no keys, no network)

```bash
mkdir -p ~/p4-container-out
podman run --rm --network none -v ~/p4-container-out:/out:Z maqs-way-p4:local
```

`--network none` is not decoration: the run has no outbound connectivity other
than the container's own loopback, where the runner starts its local stub
embedder/chat server. The run needs no API keys, and `run.sh` unsets the
provider variables at start, so keys inherited from the host (or passed with
`-e`) cannot affect it.

The report is copied to `~/p4-container-out/p4_mem0_isolation_report.json`
(the path inside the image is `/app/evals/results/`, a throwaway copy). Print
of interest, from the run itself:

- `CONFIG_SHA256 = 548343f61ef4…` — the config fingerprint; it must equal the
  value in the committed artifact;
- `passed: True`, identical `main`/`controls` counters.

Two container runs on 2026-11-10 matched the committed artifact on
`provenance.config_sha256`, `passed`, `main`, `controls` and
`control_inconclusive`; only `provenance.date`,
`observed_behavior.foreign_memory_id` and `environment.uname` differed. They
are recorded in `evals/results/p4_rerun_log.md` (section "Container
reproductions"). A
container artifact is a reproduction check, not a new verdict, and is not
committed.
