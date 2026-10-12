# Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) speaks the Anthropic **Messages** API,
which alcf-proxy serves at `/v1/messages`.

## 1. Start the proxy

```bash
alcf-proxy serve        # http://localhost:<PORT>
```

## 2. Point Claude Code at the proxy

### Option A: Configuration file (`~/.claude/settings.json`)

To make your configuration persistent without polluting global environment variables, configure `~/.claude/settings.json`:

```json
{
  "apiKeyHelper": "echo dummy",
  "env": {
    "ANTHROPIC_BASE_URL": "http://localhost:<PORT>",
    "ANTHROPIC_AUTH_TOKEN": "dummy",
    "ANTHROPIC_DEFAULT_OPUS_MODEL": "inkling-bf16[1m]",
    "ANTHROPIC_DEFAULT_SONNET_MODEL": "inkling-bf16[1m]",
    "ANTHROPIC_DEFAULT_HAIKU_MODEL": "inkling-bf16[1m]"
  }
}
```

### Option B: Environment variables

Claude Code reads the Anthropic base URL from environment variables. Set the base URL to the proxy's
**host root** (Claude Code appends `/v1/messages` itself) and use a dummy key:

=== "Linux / macOS"

    ```bash
    export ANTHROPIC_BASE_URL="http://localhost:<PORT>"
    export ANTHROPIC_API_KEY="dummy"
    claude --model "inkling-bf16[1m]"
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:ANTHROPIC_BASE_URL = "http://localhost:<PORT>"
    $env:ANTHROPIC_API_KEY = "dummy"
    claude --model "inkling-bf16[1m]"
    ```

=== "Windows (cmd)"

    ```bat
    set ANTHROPIC_BASE_URL=http://localhost:<PORT>
    set ANTHROPIC_API_KEY=dummy
    claude --model "inkling-bf16[1m]"
    ```

## Choosing the model & Context window `[1m]` syntax

Minerva serves `inkling-bf16` with a **1,048,576 token (1M) context window**, tool calling, and thinking token support.

Claude Code allows specifying context window size by appending `[1m]`, `[200k]`, etc. to custom model names:
```bash
claude --model "inkling-bf16[1m]"
```

- **Client side**: Claude Code uses `[1m]` to allocate a 1M token budget and avoids truncating context to the default 200k tokens.
- **Proxy side**: `alcf-proxy` automatically detects and strips `[1m]` (and similar suffix tags like `[200k]` or `alcf:` prefixes), routing cleanly to the upstream cluster's `inkling-bf16` model.
- **Failback support**: Claude Code may internally invoke subagents or summary calls using `claudesonnet5` or `claude-3-5-haiku`. You can set `ALCF_PROXY_UNKNOWN_MODEL_FALLBACK="inkling-bf16"` so any unrecognized model names seamlessly fall back to your preferred model.

!!! note "How translation works"
    Claude Code sends Anthropic Messages requests with streaming SSE; alcf-proxy converts them to ALCF upstream requests and converts streamed replies back into Anthropic SSE event frames (`event: message_start` → `event: content_block_delta` → `event: message_stop`). If Claude Code ever falls back to non-streaming requests (`stream: false`), the proxy aggregates upstream chunks into a standard Anthropic Message JSON response.

## Don't disturb an existing argo / default setup

`ANTHROPIC_BASE_URL` only affects the shell/session where you set it. To switch back to your normal
Claude Code backend, unset it:

=== "Linux / macOS"

    ```bash
    unset ANTHROPIC_BASE_URL ANTHROPIC_API_KEY
    ```

=== "Windows (PowerShell)"

    ```powershell
    Remove-Item Env:ANTHROPIC_BASE_URL, Env:ANTHROPIC_API_KEY
    ```

## Troubleshooting

- **Empty replies / hangs** — check `alcf-proxy health`; the upstream cluster may be down (failover
  should kick in). See [Troubleshooting](../troubleshooting.md).
- **Auth errors** — the dummy key is fine; real auth is the proxy's job. Run `alcf-proxy auth status`
  to confirm the proxy itself is authenticated.
