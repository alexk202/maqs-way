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
- SMOKE FULL-PIPELINE RESULT (2026-10-16T22:05Z): deviation RESOLVED — Llama-3.1-8B-Instruct Q4_K_M (bartowski) runs on OUR llama.cpp server :8085 (llama-cpp-retina build, ctx 16384, Vulkan, temp per-request 0 from Mem0). infer=True: 5/5 facts extracted+recalled. Extraction cost: first call 144.7s (warm-up), then 21-30s/fact; retrieval ~0s. Both Q5 LM Studio instances unloaded per owner instruction (VRAM 14.8→2.2GB). Still synthetic smoke, NOT benchmark; no calibration numbers. Extraction throughput makes bulk LoCoMo runs a separate sizing decision (115K-context datasets exceed 16k ctx — needs map-reduce or long-ctx model, owner call).

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
