# ALCF-proxy

[![PyPI version](https://img.shields.io/pypi/v/alcf-proxy?color=green)](https://pypi.org/project/alcf-proxy/)
[![Python versions](https://img.shields.io/pypi/pyversions/alcf-proxy)](https://pypi.org/project/alcf-proxy/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

**alcf-proxy** is a standalone, cross-platform **translating gateway** for
[ALCF inference endpoints](https://docs.alcf.anl.gov/services/inference-endpoints/). Run one local
proxy and point any OpenAI- or Anthropic-style coding CLI at it — **Codex, Claude Code, Aider,
OpenCode**, and more — without each tool needing to know about ALCF's auth or wire format.

Inspired by [argo-proxy](https://github.com/Oaklight/argo-proxy), but the upstream is ALCF's public
Bearer-authenticated gateway (not ANL ARGO), and the proxy manages ALCF's rotating token for you.

## Why

ALCF's gateway is OpenAI-compatible, but each coding CLI speaks a slightly different wire format and
none of them know how to fetch/refresh an ALCF Globus token. alcf-proxy sits in the middle:

```
  your CLI  ──►  alcf-proxy (localhost)  ──►  ALCF inference gateway
  (chat / responses / messages)   translate + inject token, stream back
```

- **One instance, three client formats** — `/v1/chat/completions` (OpenAI SDK, Aider, OpenCode),
  `/v1/responses` (Codex), `/v1/messages` (Claude Code).
- **Real streaming** — every request is translated to ALCF's streaming `chat/completions` upstream
  and streamed back token-by-token in the client's format (via
  [llm-rosetta](https://github.com/Oaklight/llm-rosetta)).
- **Built-in auth** — one-time Globus browser login; the proxy caches and auto-refreshes the ~48h
  access token. Clients just use a dummy key.
- **Endpoint failover** — if a cluster is under maintenance, the proxy fails over to the next one and
  remaps the per-endpoint model id automatically.
- **Cross-platform** — Linux, macOS, Windows. Pure Python.

## 60-second start

```bash
pip install alcf-proxy
alcf-proxy auth login     # one-time Globus browser login
alcf-proxy serve          # gateway on http://localhost:11445
```

Then point your CLI at `http://localhost:11445/v1` with any dummy API key. See
[Quickstart](quickstart.md) and [Connect a CLI](clients/index.md).

## Next steps

<div class="grid cards" markdown>

- :material-download: **[Installation](installation.md)** — pip, uvx, or from source
- :material-key: **[Authentication](authentication.md)** — one-time Globus login (all platforms)
- :material-rocket-launch: **[Quickstart](quickstart.md)** — start the proxy, send a request
- :material-connection: **[Connect a CLI](clients/index.md)** — Codex, Claude Code, OpenCode, Aider

</div>
