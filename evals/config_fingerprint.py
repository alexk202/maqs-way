"""Config fingerprint helper (PREREG_TEMPLATE.md v1 sec 2; owner-sanctioned
2026-10-26 after the full-500-iso gate audit: gates must be derived from the
run's ACTUAL config, and the prereg must reference the config's hash, not a
belief about it).

announce(facts, llm_base_url) -- call as the FIRST statement of a runner's
main():
  1. merges the runner's stable config facts with LIVE server facts
     (llama-server /slots: n_ctx, seed, temperature, repeat_penalty -- the
     client cannot be lied to about the server flags it actually runs);
  2. canonicalizes (sorted keys, compact JSON) and sha256-hashes the payload;
  3. prints 'CONFIG_SHA256 = <hash>' as the run's first stdout line;
  4. EXPECTED_CONFIG_SHA256 env set and != hash -> 'CONFIG MISMATCH' and
     sys.exit(2) BEFORE any server request (the run does not start);
  5. returns the provenance block {config_sha256, config_effective} to embed
     into the artifact's provenance.

Model file md5: computed if MODEL_FILE env points at the gguf; taken from
MODEL_MD5 env if only the digest is known; else null (the md5 remains a
stand-checklist item; the hash payload records which of the three happened).

The extraction flow and request parameters are NOT touched by this helper.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request


def _server_facts(llm_base_url):
    """Live server facts from llama-server /slots (n_ctx, default params)."""
    root = llm_base_url.rsplit("/v1", 1)[0]
    try:
        with urllib.request.urlopen(f"{root}/slots", timeout=5) as r:
            slots = json.load(r)
        s0 = slots[0] if slots else {}
        p = s0.get("params", {}) or {}
        return {"n_ctx": s0.get("n_ctx"), "seed": p.get("seed"),
                "temperature_server": p.get("temperature"),
                "repeat_penalty_server": p.get("repeat_penalty"),
                "top_k_server": p.get("top_k"), "top_p_server": p.get("top_p")}
    except Exception as e:  # foreign OpenAI-compatible server without /slots
        return {"n_ctx": None, "slots_endpoint": f"unavailable: {type(e).__name__}"}


def _model_md5():
    path = os.environ.get("MODEL_FILE")
    if path:
        h = hashlib.md5()
        with open(path, "rb") as fh:
            for chunk in iter(lambda: fh.read(1 << 22), b""):
                h.update(chunk)
        return {"source": "MODEL_FILE", "md5": h.hexdigest()}
    md5 = os.environ.get("MODEL_MD5")
    if md5:
        return {"source": "MODEL_MD5", "md5": md5}
    return {"source": "not-set", "md5": None}


def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def announce(facts, llm_base_url, label=None):
    """Print the config hash, enforce EXPECTED_CONFIG_SHA256, return the
    provenance block. Exits 2 on mismatch BEFORE any server request."""
    payload = dict(facts)
    payload["server"] = _server_facts(llm_base_url)
    payload["model_file"] = _model_md5()
    payload["_fingerprint_meta"] = {"ts": int(time.time()), "label": label}
    # ts+label are meta: EXCLUDE from the hash so the hash is reproducible
    hashable = {k: v for k, v in payload.items() if k != "_fingerprint_meta"}
    sha = hashlib.sha256(canonical(hashable).encode()).hexdigest()
    print(f"CONFIG_SHA256 = {sha}", flush=True)
    if label:
        print(f"CONFIG_LABEL = {label}", flush=True)
    expected = os.environ.get("EXPECTED_CONFIG_SHA256")
    if expected and expected.strip() and expected.strip() != sha:
        print(f"CONFIG MISMATCH: expected {expected.strip()}, actual {sha} "
              f"-- refusing to start (prereg assert)", flush=True)
        sys.exit(2)
    return {"config_sha256": sha, "config_effective": hashable}
