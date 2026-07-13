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
- **Manages the ALCF token**: authenticates via Globus (built in — no external script needed),
  injects the token as a Bearer header, and refreshes automatically when it nears its ~48h expiry.
  Clients just use a dummy key.
- **Endpoint auto-failover**: if a cluster returns 503 / is under maintenance, the proxy advances to
  the next configured endpoint (remapping the per-endpoint model id) and sticks to the one that works.

## Prerequisites

- **Python ≥ 3.10.** All auth is built in (via `globus-sdk`, installed automatically); you do **not**
  need ALCF's `inference_auth_token.py`.
- **First-time login** (once): `alcf-proxy auth login` — opens a browser for Globus OAuth and stores
  the token in globus-sdk's standard per-platform location (resolved correctly on Linux/macOS/Windows;
  check it any time with `alcf-proxy auth status`). The refresh token then lasts months.

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
- The token is stored by `globus-sdk` in its standard per-platform app-data dir (on **Windows** this
  is under `%LOCALAPPDATA%`, resolved automatically — no hard-coded `~/.globus` path). Just run
  `alcf-proxy auth login` once; `alcf-proxy auth status` prints the exact path in use.
- Binding to a non-loopback host (`--host 0.0.0.0`) is refused unless `ALCF_PROXY_API_KEY` is set,
  because the proxy injects your real ALCF token for every caller.

### First-time login

Run this once per machine before `serve` / `models`:

```bash
alcf-proxy auth login
```

It opens your default browser for Globus OAuth and starts a short-lived local callback server to
receive the result, then stores the refresh + access tokens (good for months) in globus-sdk's
per-platform location. Verify with `alcf-proxy auth status`.

- **Windows / macOS / Linux desktop**: works out of the box — the browser opens and the local
  callback completes automatically. No `~/.globus` path is assumed; the token location is whatever
  globus-sdk chooses for your OS (`%LOCALAPPDATA%` on Windows), shown by `auth status`.
- **Headless / remote (SSH, no local browser)**: the local-callback flow needs a browser that can
  reach `localhost` on the login machine. If you're on a headless box, run `alcf-proxy auth login`
  on a machine that has a browser using the **same OS user profile / token dir**, or forward the
  callback port over SSH. (A copy-paste device-code fallback is not yet implemented.)

## Usage

```bash
alcf-proxy auth login                     # one-time Globus browser login
alcf-proxy auth status                    # authenticated? token path + hours left
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
  alcf_auth.py           # internalized Globus auth (cross-platform token storage)
  auth.py                # TokenManager: in-process fetch + refresh-on-expiry
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
