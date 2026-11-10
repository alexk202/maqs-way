# repro/Dockerfile -- one-command P4 reproduction (MAQS-Way).
#
# Build context is the REPOSITORY ROOT (requirements.txt and evals/ are copied
# from there); the context is only read, nothing is written back to the host.
#
#   podman build -f repro/Dockerfile -t maqs-way-p4:local .
#
# Base image is pinned by digest (index digest of docker.io/library/python:
# 3.12.2-slim, resolved 2026-11-10 via `podman image inspect`). The full
# registry-qualified name is required: podman does not assume docker.io for a
# bare `python:...` reference.
FROM docker.io/library/python:3.12.2-slim@sha256:5dc6f84b5e97bfb0c90abfb7c55f3cacc2cb6687c8f920b64a833a2219875997

# git is needed for the git+https pin of mem0 (requirements.txt); nothing else
# is installed. BUILD TIME needs network (base image + packages); the run
# itself is executed with --network none, see run.sh and README.md.
RUN apt-get update \
 && apt-get install -y --no-install-recommends git \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir --disable-pip-version-check -r requirements.txt

# Only what the run needs: the evaluation code (evals/config_fingerprint.py is
# imported by the runner) plus the entrypoint below. The host repository is
# never mounted.
COPY evals/ ./evals/
COPY repro/run.sh ./run.sh
RUN chmod 0755 ./run.sh \
 && rm -f ./evals/results/p4_mem0_isolation_report.json
# ^ the image must not fall back to a stale committed artifact if the run dies
#   before writing its own report: the copy inside the image starts without one.

ENTRYPOINT ["/app/run.sh"]
