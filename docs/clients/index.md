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
http://localhost:11445/v1
```

(For Anthropic clients that append `/v1/messages` themselves, use the host root
`http://localhost:11445` — see the [Claude Code](claude-code.md) page.)

## Before you start

1. `alcf-proxy auth login` (once) — see [Authentication](../authentication.md)
2. `alcf-proxy serve` — keep it running in a terminal (or as a background service)

## Pick your tool

<div class="grid cards" markdown>

- :material-robot: **[Codex](codex.md)** — OpenAI's coding CLI (`/v1/responses`)
- :material-brain: **[Claude Code](claude-code.md)** — Anthropic's coding CLI (`/v1/messages`)
- :material-code-braces: **[OpenCode](opencode.md)** — `/v1/chat/completions`
- :material-console: **[Aider & OpenAI SDK](openai-compatible.md)** — anything OpenAI-compatible

</div>

!!! tip "Model ids"
    Use the id for the cluster you're serving: `openai/gpt-oss-120b` (sophia/vllm) or `gpt-oss-120b`
    (metis/api). Run `alcf-proxy models` to list exact ids.
