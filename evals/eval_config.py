"""Shared eval runtime config (reproducibility package, 2026-10-24).

All server/model parameters come from environment variables with the
project-stand defaults baked in. A foreign stand (different ports, Ollama,
LM Studio, another model) reproduces the pipeline by exporting its own
values -- no code edits needed. See evals/REPRODUCE.md.

Env vars:
  LLM_BASE_URL    default http://127.0.0.1:8085/v1   (OpenAI-compatible chat)
  EMBED_BASE_URL  default http://127.0.0.1:1449/v1   (OpenAI-compatible embeddings)
  LLM_MODEL       default Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf
  EMBED_MODEL     default text-embedding-nomic-text... see below
  EMBED_DIMS      default 768
  LLM_API_KEY     default: contents of LLM_API_KEY_FILE, else "local"
  LLM_API_KEY_FILE default /tmp/opencode/pilot8085.key (stand convention;
                   llama-server without --api-key accepts any bearer)
  EMBED_API_KEY   default "local-smoke" (LM Studio ignores it)
"""
import os


def _env(name, default):
    return os.environ.get(name, default)


LLM_BASE_URL = _env("LLM_BASE_URL", "http://127.0.0.1:8085/v1")
EMBED_BASE_URL = _env("EMBED_BASE_URL", "http://127.0.0.1:1449/v1")
LLM_MODEL = _env("LLM_MODEL", "Meta-Llama-3.1-8B-Instruct-Q4_K_M.gguf")
EMBED_MODEL = _env("EMBED_MODEL", "text-embedding-nomic-embed-text-v1.5")
EMBED_DIMS = int(_env("EMBED_DIMS", "768"))
EMBED_API_KEY = _env("EMBED_API_KEY", "local-smoke")


def _llm_key():
    k = os.environ.get("LLM_API_KEY")
    if k:
        return k
    keyfile = os.environ.get("LLM_API_KEY_FILE", "/tmp/opencode/pilot8085.key")
    try:
        with open(keyfile) as fh:
            return fh.read().strip()
    except OSError:
        # llama-server launched without --api-key accepts any bearer value
        return "local"


LLM_API_KEY = _llm_key()
