# Connect a CLI

alcf-proxy exposes three OpenAI/Anthropic-compatible endpoints on one instance. Point your tool at
the matching one, using **any dummy API key** (the proxy injects the real ALCF token).

| Endpoint | Wire format | Tools that use it |
|----------|-------------|-------------------|
| `/v1/chat/completions` | OpenAI Chat | OpenAI SDK, Aider, OpenCode, most generic clients |
| `/v1/responses` | OpenAI Responses | Codex CLI |
| `/v1/messages` | Anthropic Messages | Claude Code |

The base URL is your proxy address:

```
http://localhost:<PORT>/v1
```

(For Anthropic clients that append `/v1/messages` themselves, use the host root
`http://localhost:<PORT>` — see the [Claude Code](claude-code.md) page.)

!!! tip "What's `<PORT>`?"
    alcf-proxy has no built-in default port — `<PORT>` is whatever you set in your local `.env`
    (`cp .env.example .env`, then set `ALCF_PROXY_PORT`) or passed via `--port`. See
    [Configuration](../configuration.md).

## Before you start

1. `alcf-proxy auth login` (once) — see [Authentication](../authentication.md)
2. `.env` set with your port, then `alcf-proxy serve` — keep it running in a terminal (or as a
   background service)

## Pick your tool

<div class="grid cards" markdown>

- :material-robot: **[Codex](codex.md)** — OpenAI's coding CLI (`/v1/responses`)
- :material-brain: **[Claude Code](claude-code.md)** — Anthropic's coding CLI (`/v1/messages`)
- :material-code-braces: **[OpenCode](opencode.md)** — `/v1/chat/completions`
- :material-console: **[Aider & OpenAI SDK](openai-compatible.md)** — anything OpenAI-compatible

</div>

!!! tip "Model ids — any of them just work"
    Since v0.2.0 the proxy does **unified routing**: request any model from `alcf-proxy models`
    (e.g. `openai/gpt-oss-120b`, `gpt-oss-120b`, `nemotron-3-ultra`) and it is routed to whichever
    cluster serves it, with automatic cross-cluster failover. No per-cluster configuration.
