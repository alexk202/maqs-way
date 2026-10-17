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
- N50 PASS, temporal slice (2026-10-17 02:30-03:24, evals/results/pilot_evidence_n50.json): selection = first-50-in-committed-order (pre-registered, no cherry-picking). RESULT: evidence-R@5 = 1.00 (50/50, zero misses), substr 0.20; cost 3237s = 64.7s/q, 54min wall, 500q ~9h single-GPU. SCOPE LABEL (honest): committed dataset is type-grouped — first-50 is 100% temporal-reasoning, so this is R@5 on the TEMPORAL slice, not the mixed benchmark. Do NOT read 1.00 as the SPEC §3.2 temporal gate — metric is evidence-retrieval, not answer-accuracy per LoCoMo/Graphiti protocol.
- STRATIFIED-50 PASS (pre-registered before run, 2026-10-17): allocation by largest remainder over the REAL 6-type distribution (133/133/78/70/56/30 of 500) -> 13 temporal / 13 multi-session / 8 knowledge-update / 7 single-session-user / 6 single-session-assistant / 3 single-session-preference = 50, first-k-per-type in committed order (deterministic, no cherry-picking; allocation computed by code, prereg corrected to match before launch — initial text omitted the preference type). Purpose: mixed-type evidence-R@5, the number the temporal-only pass cannot give.
- STRATIFIED-50 RESULT (2026-10-17T07:36Z, evals/results/pilot_evidence_n50_stratified.json): evidence-R@5 = 0.98 (49/50), substr 0.16; cost 2899s = 48.3min wall, ~8.1h per 500q single-GPU. Allocation held exactly (13/13/8/7/6/3). Single miss: single-session-user, answer "The Glass Menagerie" absent from top-5 (retrieval near-miss, not pipeline failure — stores populated, other 4 types clean; "near-miss" is a description, hypothesis for cause — rare quoted title vs embeddings — stays a hypothesis until a second slice shows a name-entity pattern). This is the WP2 mixed-type number, single-point on Mem0@0724291 + Llama-3.1-8B Q4 ctx 32768, retrieval-side metric (no generation/judge yet).
- PREREG DISCREPANCY LABEL (per Lumín taxonomy, decided 2026-10-17): **posthoc**. Fact: prereg line "R@5 LongMemEval oracle: [0.4, 0.9]" (line 28) NAMED the oracle subset, but the range was set blind (no dataset in hand, no condition-differentiated reasoning recorded). The "full-haystack assumption" claim in the earlier explanation is itself post-hoc interpretation, not a pre-registered condition. Verdict: prereg_match: posthoc — the range was non-interpretable at prereg time, so it was neither "met" nor "exceeded"; the measured number stands on its own provenance, the explanation stands labeled as found-after. Both numbers recorded: expected [0.4, 0.9] (guess, condition-blind) / measured 0.98 (oracle-subset by design).
- ADDENDUM (Lumín refinement, 2026-10-17, append-only): split label — `prereg_selection: verified` (allocation/selection held exactly as pre-registered, 13/13/8/7/6/3, first-k-per-type), `prereg_expectation: posthoc` (range was condition-blind). Two facts, never merged into one "posthoc".
- STATISTICAL NOTE (Lumín): 49/50 Wilson 95% CI ≈ [0.895, 0.997]; 50/50 ≈ [0.929, 1.000] — overlapping. The two passes are statistically indistinguishable at n=50: "within n=50 uncertainty", NOT "mixed dipped below temporal". What IS visible: the method holds the same on 6 types as on 1.
- SUBSTR SEMANTICS (per Stasik request, one sentence): substr = exact case-insensitive substring of the gold answer string inside the concatenation of the top-5 retrieved memory texts; evidential only when extraction preserves phrasing verbatim (paraphrase-heavy extraction makes substr a lower bound, reported for transparency).
- WP3 PROPOSAL (Lumín, adopted as backlog): mandatory `conditions` block in scoreboard schema — {slice, haystack, n, metric_type, prereg_ref, prereg_match: yes|mismatch|posthoc} as a validator: a measurement without it is rejected. Closes the three-times-repeated lesson (scope / gate_target_basis / haystack_condition).
- R@5=0.00 is VOID as a quality metric (prereg kill-condition: explain, not smooth): the matcher compared answer SUBSTRINGS against extracted-fact prose; extraction paraphrases ("GPS system not functioning correctly" -> "issue with their car's GPS system on 3/22"), so string/token matching undercounts. Standard LongMemEval protocol = answer generation + judge, or evidence-session retrieval tagging — NOT fact-prose substring. Metric implementation fix = next pass, protocol per official repo.
- COST (measured, RTX 5060 Ti sequential, ctx 32768): ingest 14-92s/session (extraction dominates), 5 questions = 259s total -> 50q ~43min, 500q ~7.2h single-GPU. Ingestion is the bottleneck; chunking bounded prompts (no ctx overflows). This is the sizing data WP2 needed; normative numbers wait for the protocol-correct metric pass.
- INFRASTRUCTURE NOTES (env-provenance class): LM Studio update flipped Vulkan numbering (Vulkan0=iGPU, Vulkan1=RTX) -> own :8085 pinned to Vulkan1; MEM0_TELEMETRY=False removes PostHog noise AND the ~/.mem0/migrations_qdrant lock that breaks multi-Memory processes; max_tokens=400 truncated extraction JSON mid-list (silent 0-fact adds) -> 1200; qdrant-local needs one path per process.
- RUNNER-GREEN (2026-10-17, scratch-runner gate CLOSED): promotion repo pipeline.yml green on real Actions runner (run 39020475401, 9s) — canon GREEN + 3 RED branches + shapes + evaluator e2e all passed remotely. Runner evidence: python 3.12.3 | jsonschema 4.10.3 vs local 3.12.2 | 4.23.0 — versions in-range, verdict identical to local baseline: no environment-dependent behavior. CI fix recorded: canon repo name alexk202/maqs-way (MAQS_Way was wrong), ref main until next canon tag. Meta-point (Prima r4): first runner-baseline data point collected.

## Expected orders of magnitude (guess, to be confronted) — PRE-GATE ERA, grandfathered, do not edit
- R@5 LongMemEval oracle: [0.4, 0.9] (gate 0.7 / target 0.85)
- temporal_accuracy: [0.4, 0.9] (gate 0.65 / target 0.8)
- abstention_rate: [0.5, 1.0] (gate 0.8 / target 0.9)
- duplicate_rate: [0.0, 0.15] (gate ≤5% / target ≤2%)
- contamination_rate: [0.0, 0.1] (gate ≤1% / target 0)
- deletion_residue: exactly 0.0 by construction (tombstone cascade)
- cross_tenant_leak: exactly 0 (negative test, not a distribution)

## Expectations (bound) — post-gate era, checked by evals/check_conditions.py --prereg
- evidence-R@5 expected [0.90, 1.00] under oracle-subset, full-500 in committed order, evidence-session metric 1a (tightens the Wilson CI of the 0.98/49-50 point from [0.895,0.997] to ~[0.97,0.995]; NOT answer-accuracy, NOT SPEC §3.2 gate)
- substr-rate expected [0.10, 0.30] under oracle-subset (paraphrase lower bound, transparency only)

## Required env provenance per number (no number without it)
{model_id, quantization, context_len, runner, date, seeds, dataset_commit}

## Kill conditions (run is void, not failed)
- Closed-API weights (drift under you) -> reject, do not record.
- Missing provenance field -> number not admitted to the table.
- Measurement inside declared range -> confirm; outside -> explain in SPEC §3.2 note, retarget only with rationale commit.
