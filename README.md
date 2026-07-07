# alcf-run

Unified CLI to launch agentic frameworks against **ALCF inference endpoints**, with shared ALCF
token handling. Currently implements the `codex` framework end-to-end; other frameworks
(`claude`, `opencode`, …) are planned.

## Why this exists

ALCF's inference gateway is OpenAI-compatible and natively supports the Responses API, **but rejects
streaming** (`stream:true`). Codex ≥0.142 always streams and has no way to disable it. `alcf-run`
bridges the gap with a tiny local proxy: it accepts codex's streaming request, forwards it to ALCF as
`stream:false` (injecting a fresh ALCF token), and re-wraps the complete reply as the SSE event
stream codex expects.

The existing **argo** setup (`localhost:11444`, the default codex provider) is never touched —
`alcf-run` only adds an `alcf_proxy` provider and manages its own profile file.

## Install

```bash
# In the target environment (must have globus_sdk for the ALCF auth script):
pip install -e .
```

Requires Python ≥3.10. Dependencies: fastapi, uvicorn, httpx, llm-rosetta[openai], tomli-w.

On Perlmutter the dev environment is `/pscratch/sd/j/jinh/envs/hack`.

## Usage

```bash
alcf-run codex                          # start proxy, launch codex on openai/gpt-oss-120b
alcf-run codex --profile alcf-llama70b  # extra args are passed through to codex
alcf-run codex "explain this repo"      # positional args passed through too
alcf-run models                         # list models currently served by ALCF
alcf-run auth                           # show ALCF token status / hours remaining
alcf-run claude                         # (not yet implemented)
```

`alcf-run codex` starts an ephemeral proxy on `localhost:11445` (falls back to a free port if
taken), points a managed `alcf_proxy` codex provider at it, runs codex, and tears the proxy down on
exit. Nothing is left running afterwards.

## How it works

```
alcf-run codex
  ├─ auth.get_token()            # fresh ALCF token via inference_auth_token.py (uses sys.executable)
  ├─ ProxyManager.start()        # uvicorn on localhost:11445
  │    POST /v1/responses:
  │      force stream=false + inject Bearer token → ALCF /v1/responses (503 cold-start retry)
  │      complete JSON → rebuild responses SSE events (llm-rosetta) → return to codex
  ├─ ensure_provider_config()    # add-only [model_providers.alcf_proxy] in $CODEX_HOME/config.toml
  │                              #   + separate alcf-gpt-oss-120b.config.toml profile (codex ≥0.142)
  ├─ exec codex --profile alcf-gpt-oss-120b
  └─ ProxyManager.stop()
```

### argo safety

- The codex config merge is **add-only**: top-level `model`/`model_provider`, `[model_providers.argo]`,
  and `[projects.*]` are left byte-for-byte intact. The existing config is backed up to
  `config.toml.alcf-run.bak` before any write, and the merge is idempotent.
- The ALCF token lives only in the proxy process memory (injected per request); it is never written
  to the codex config or any file.

## Layout

```
alcf_run/
  cli.py              # unified dispatcher
  config.py           # constants + env resolution (CODEX_HOME, auth script path)
  auth.py             # ALCF token via inference_auth_token.py
  endpoints.py        # ALCF URL builder + model list
  proxy/
    server.py         # FastAPI: stream→non-stream bridge + token injection
    sse.py            # rebuild complete JSON into responses SSE events (llm-rosetta)
    manager.py        # ephemeral proxy lifecycle
  frameworks/
    base.py           # Framework interface
    codex.py          # config merge + launch
```

## Tests

```bash
python -m pytest              # unit tests (offline, use captured fixtures)
python tests/manual_live_proxy.py    # live end-to-end proxy smoke (needs a valid ALCF token)
ALCF_RUN_LIVE=1 python -m pytest     # also run the proxy manager live smoke
```

Unit tests use real ALCF response fixtures under `tests/fixtures/` (captured once; contain only model
output, no secrets).
