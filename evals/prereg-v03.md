# WP2 pre-registration (calibration expectations BEFORE the first run)

Status: expectations, not results. Recorded 2026-10-16 to prevent circular
retargeting (measure -> adjust gates to fit the measurement). After the run,
discrepancies are explained, not smoothed over. Numbers below are wide
guesses labeled as such; the run decides.

## Candidate system (council: reproducible over representative)
Mem0@0724291 (SHA pinned, audit exists), open-weights model, version-pinned,
local runner. Alternative Qwen2-7B/Llama-3.1-8B fixed commit — owner picks
before launch; single-point calibration either way (normative only after ≥2 systems).

## Chosen system (2026-10-16, smoke-tested)
- model_id: `lmstudio-community/meta-llama-3.1-8b-instruct` (5.34 GiB, Q4 class), served by LM Studio server on `127.0.0.1:1449`, OpenAI-compatible `/v1/chat/completions`, no auth on loopback.
- smoke probe: `temperature: 0, max_tokens: 5` → `ready` in 6.3s, usage reported (prompt 98 / completion 2). Server state untouched (Финик stays unloaded; llama-servers on :8080/:8083 untouched).
- SUT: Mem0@0724291 (isolated venv `~/Projects/mem0-pilot-venv`, embedded Qdrant in /tmp, no external services).
- DEVIATION (labeled, owner-visible): LM Studio build rejects `response_format: json_object` (Mem0 extraction requirement) even after update → pilot LLM runs on :8080 `Qwen3.5-4B-Q4_K_M.gguf` (iGPU, temperature 0 per request); embedder stays :1449 nomic. Single-point on Qwen ≠ Llama pick; numbers (when real) carry this provenance instead of hiding it.
- Pilot: 5 synthetic memory facts (labeled synthetic, NOT benchmark) → then 50 LongMemEval-oracle R@5 + 20 temporal after datasets vendored.
- SMOKE RESULT (2026-10-16T21:55Z): 5/5 recalled via Mem0 raw pipeline (`infer=False`), latencies 0.0-2.7s/probe. Honest scope: LLM extraction path UNTESTED — stock extraction prompt ~8220 tokens vs server ctx 8192 on :8080; exercising it needs a server context bump (owner call, NOT done without permission). No calibration numbers claimed from this smoke.
- SMOKE FULL-PIPELINE RESULT (2026-10-16T22:05Z): deviation RESOLVED — Llama-3.1-8B-Instruct Q4_K_M (bartowski) on OWN llama.cpp server :8085, infer=True 5/5 synthetic. (Details superseded by N5 pilot below.)
- N5 PILOT (2026-10-16T23:02 + 23:1x rerun, LongMemEval-oracle): pipeline mechanics VALIDATED end-to-end (oracle sessions -> Mem0 infer=True extraction 7-12 facts/session -> stored 7-31 points -> retrieval returns evidence: q0 top-2 IS the GPS answer memory, score 0.695). One env flake found: first rerun's searches returned empty while stores were healthy; identical rerun returned 5 results/question — classified as LM Studio post-update flake, not canon code.
- R@5=0.00 is VOID as a quality metric (prereg kill-condition: explain, not smooth): the matcher compared answer SUBSTRINGS against extracted-fact prose; extraction paraphrases ("GPS system not functioning correctly" -> "issue with their car's GPS system on 3/22"), so string/token matching undercounts. Standard LongMemEval protocol = answer generation + judge, or evidence-session retrieval tagging — NOT fact-prose substring. Metric implementation fix = next pass, protocol per official repo.
- COST (measured, RTX 5060 Ti sequential, ctx 32768): ingest 14-92s/session (extraction dominates), 5 questions = 259s total -> 50q ~43min, 500q ~7.2h single-GPU. Ingestion is the bottleneck; chunking bounded prompts (no ctx overflows). This is the sizing data WP2 needed; normative numbers wait for the protocol-correct metric pass.
- Infrastructure notes (env-provenance class): LM Studio update flipped Vulkan numbering (Vulkan0=iGPU, Vulkan1=RTX) -> own :8085 pinned to Vulkan1; MEM0_TELEMETRY=False removes PostHog noise AND the ~/.mem0/migrations_qdrant lock that breaks multi-Memory processes; max_tokens=400 truncated extraction JSON mid-list (silent 0-fact adds) -> 1200; qdrant-local needs one path per process.

## Expected orders of magnitude (guess, to be confronted)
- R@5 LongMemEval oracle: [0.4, 0.9] (gate 0.7 / target 0.85)
- temporal_accuracy: [0.4, 0.9] (gate 0.65 / target 0.8)
- abstention_rate: [0.5, 1.0] (gate 0.8 / target 0.9)
- duplicate_rate: [0.0, 0.15] (gate ≤5% / target ≤2%)
- contamination_rate: [0.0, 0.1] (gate ≤1% / target 0)
- deletion_residue: exactly 0.0 by construction (tombstone cascade)
- cross_tenant_leak: exactly 0 (negative test, not a distribution)

## Required env provenance per number (no number without it)
{model_id, quantization, context_len, runner, date, seeds, dataset_commit}

## Kill conditions (run is void, not failed)
- Closed-API weights (drift under you) -> reject, do not record.
- Missing provenance field -> number not admitted to the table.
- Measurement inside declared range -> confirm; outside -> explain in SPEC §3.2 note, retarget only with rationale commit.
