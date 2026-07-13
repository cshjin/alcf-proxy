# alcf-proxy

A standalone, cross-platform **translating gateway** for [ALCF inference
endpoints](https://docs.alcf.anl.gov/services/inference-endpoints/). Run one local proxy and point
any OpenAI- or Anthropic-style coding CLI at it — Codex, Claude Code, Aider, OpenCode, and more —
without each tool needing to know about ALCF's auth or wire format.

Inspired by [argo-proxy](https://github.com/Oaklight/argo-proxy), but the upstream is ALCF's public
Bearer-authenticated gateway (not ANL ARGO), and the proxy manages ALCF's rotating token for you.

## What it does

- **Speaks 3 client formats** on one instance:
  - `/v1/chat/completions` — OpenAI SDK, Aider, OpenCode
  - `/v1/responses` — Codex CLI
  - `/v1/messages` — Claude Code
- **Translates** every request to ALCF's streaming `chat/completions` upstream via
  [llm-rosetta](https://github.com/Oaklight/llm-rosetta), and translates the streamed reply back to
  the client's format — real token-by-token streaming.
- **Manages the ALCF token**: fetches it via ALCF's Globus auth script, injects it as a Bearer
  header, and refreshes automatically when it nears its ~48h expiry. Clients just use a dummy key.
- **Endpoint auto-failover**: if a cluster returns 503 / is under maintenance, the proxy advances to
  the next configured endpoint (remapping the per-endpoint model id) and sticks to the one that works.

## Prerequisites

- **Python ≥ 3.10.**
- **ALCF's `inference_auth_token.py`** on your machine, and the interpreter you run alcf-proxy with
  must have `globus_sdk` installed (that's what the auth script imports). First-time login:
  `python ~/inference_auth_token.py authenticate` (opens a browser for Globus OAuth).

## Install

```bash
# from source (this repo)
pip install .
# or editable, for development
pip install -e .
```

Or run without installing, using [uv](https://docs.astral.sh/uv/):

```bash
uvx --from . alcf-proxy serve        # one-shot from a checkout
uvx alcf-proxy serve                 # after PyPI registration
```

### Platform notes

- **Linux / macOS / Windows** are all supported (pure Python; config paths resolved via
  `platformdirs`). Config lives at `~/.config/alcf-proxy/config.yaml` (Linux),
  `~/Library/Application Support/alcf-proxy/config.yaml` (macOS), or
  `%APPDATA%\alcf-proxy\config.yaml` (Windows).
- On **Windows**, ensure `globus_sdk` is installed in the same environment and complete the
  browser-based `authenticate` step once.

## Usage

```bash
alcf-proxy serve                          # start the gateway (reads config or uses defaults)
alcf-proxy serve --port 8080 --host 0.0.0.0
alcf-proxy serve --cluster metis --framework api --model gpt-oss-120b
alcf-proxy models                         # list models currently served by ALCF
alcf-proxy models --json                  # machine-readable
alcf-proxy health                         # token status / hours remaining
alcf-proxy config init                    # write a starter config file
alcf-proxy config show                    # print the effective config
```

### Point your CLI at it

Codex (`~/.codex/config.toml` or `$CODEX_HOME/config.toml`):

```toml
[model_providers.alcf]
name = "ALCF (via alcf-proxy)"
base_url = "http://localhost:11445/v1"
wire_api = "responses"
# no api key needed — the proxy injects the real ALCF token; set a dummy if the client requires one
```

Any OpenAI-compatible client (Aider, OpenCode, OpenAI SDK): set the base URL to
`http://localhost:11445/v1` and any non-empty API key.

Claude Code: set the Anthropic base URL to `http://localhost:11445` and any dummy key.

## Configuration

YAML file (search order: `./config.yaml`, then the platform user-config dir). CLI flags and
`ALCF_PROXY_*` env vars override the file. See [`config.example.yaml`](config.example.yaml) for all
options, including the optional explicit `endpoints:` failover list.

Precedence: **CLI flags > env (`ALCF_PROXY_*`) > config file > built-in defaults.**

## How it works

```
client (chat / responses / messages)
      │  request
      ▼
  alcf-proxy  ──translate(req)──►  IR  ──►  ALCF chat/completions (stream:true) + Bearer(auto)
      ▲                                            │  real streamed chat chunks
      │  client-format SSE  ◄──translate(stream)── IR ◄──
      │
      └─ EndpointSelector: on 503/maintenance, fail over to the next endpoint (sticky)
```

The ALCF token lives only in the proxy process memory; it is never written to any client config.

## Layout

```
alcf_proxy/
  cli.py                 # serve / models / health / config
  config.py              # YAML + env + CLI config; endpoint failover list
  auth.py                # TokenManager: fetch + refresh-on-expiry (via sys.executable)
  endpoints.py           # ALCF URLs + model listing
  upstream.py            # chat streaming client + EndpointSelector (failover)
  translate.py           # llm-rosetta engine: frontend <-> IR <-> chat
  sse.py                 # SSE codec
  server.py              # FastAPI: 3 translating routes + /v1/models + /health
  formats/               # registry (chat/responses/anthropic) + chat sanitizers
```

## Tests

```bash
python -m pytest                          # unit tests (offline); enforces coverage ≥85%
python -m pytest -m live -o addopts=""    # live end-to-end tests (need a valid ALCF token + up cluster)
```

Unit tests use real ALCF response fixtures under `tests/fixtures/` (captured once; model output
only, no secrets).

## License

MIT — see [LICENSE](LICENSE).
