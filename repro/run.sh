#!/usr/bin/env bash
# repro/run.sh -- one-command P4 run inside the image built from
# repro/Dockerfile. Executed as the image ENTRYPOINT, with no network
# (--network none): everything needed is baked in, no provider keys, no
# outbound requests. The local stub server binds on 127.0.0.1, which exists
# in the network namespace even with --network none.
#
#   podman run --rm --network none -v ~/p4-container-out:/out:Z maqs-way-p4:local
set -u

cd /app || exit 1

# Environment insensitivity: a provider key inherited from the host or passed
# with -e must not change the run (mem0's OpenAI LLM wrapper prefers
# OPENROUTER_API_KEY over the harness openai_base_url, evals/REPRODUCE.md
# sec 9). Clear the provider variables explicitly.
unset OPENROUTER_API_KEY OPENAI_API_KEY OPENAI_BASE_URL ANTHROPIC_API_KEY \
      AZURE_OPENAI_API_KEY GOOGLE_API_KEY GEMINI_API_KEY DEEPSEEK_API_KEY
echo "env: provider keys unset (OPENROUTER_API_KEY OPENAI_API_KEY OPENAI_BASE_URL" \
     "ANTHROPIC_API_KEY AZURE_OPENAI_API_KEY GOOGLE_API_KEY GEMINI_API_KEY DEEPSEEK_API_KEY)"

# config_fingerprint.announce() folds MODEL_FILE / MODEL_MD5 into the hashed
# payload (provenance.config_effective.model_file); clear them too so the run
# is not affected by inherited environment.
unset MODEL_FILE MODEL_MD5

START=$(date +%s)
python3 evals/p4_mem0_isolation.py
RC=$?
END=$(date +%s)
DURATION=$((END - START))

REPORT=evals/results/p4_mem0_isolation_report.json
echo
if [ -f "$REPORT" ]; then
    python3 - "$REPORT" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
p = d.get("provenance", {})
print("provenance.config_sha256 :", p.get("config_sha256"))
print("passed                   :", d.get("passed"))
print("control_inconclusive     :", d.get("control_inconclusive"))
env = d.get("environment", {})
print("environment.uname        :", env.get("uname"))
print("environment.python       :", env.get("python"))
print("environment.pip_freeze_mem0:", env.get("pip_freeze_mem0"))
PY
else
    echo "report not found: $REPORT (the run did not reach the report write)" >&2
fi

echo "wall clock: ${DURATION} s"

if [ -d /out ]; then
    if [ -f "$REPORT" ]; then
        cp "$REPORT" /out/p4_mem0_isolation_report.json
        echo "report copied to: /out/p4_mem0_isolation_report.json"
    else
        echo "nothing copied to /out: no report" >&2
    fi
else
    echo "/out not mounted; report left at /app/$REPORT"
fi

exit "$RC"
