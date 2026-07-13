# Claude Code

[Claude Code](https://docs.anthropic.com/en/docs/claude-code) speaks the Anthropic **Messages** API,
which alcf-proxy serves at `/v1/messages`.

## 1. Start the proxy

```bash
alcf-proxy serve        # http://localhost:11445
```

## 2. Point Claude Code at the proxy

Claude Code reads the Anthropic base URL from environment variables. Set the base URL to the proxy's
**host root** (Claude Code appends `/v1/messages` itself) and use a dummy key:

=== "Linux / macOS"

    ```bash
    export ANTHROPIC_BASE_URL="http://localhost:11445"
    export ANTHROPIC_API_KEY="dummy"
    claude
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:ANTHROPIC_BASE_URL = "http://localhost:11445"
    $env:ANTHROPIC_API_KEY = "dummy"
    claude
    ```

=== "Windows (cmd)"

    ```bat
    set ANTHROPIC_BASE_URL=http://localhost:11445
    set ANTHROPIC_API_KEY=dummy
    claude
    ```

To make it persistent, add those exports to your shell profile (`~/.bashrc`, `~/.zshrc`) or set them
as user environment variables on Windows.

## Choosing the model

alcf-proxy forwards to its configured ALCF model (default `openai/gpt-oss-120b`). If you want a
specific model and your Claude Code version lets you set one, use the id for the active cluster
(`alcf-proxy models` lists them). Otherwise the proxy's `default_model` / active endpoint is used.

!!! note "How translation works"
    Claude Code sends Anthropic Messages requests; alcf-proxy converts them to ALCF's streaming chat
    upstream and converts the streamed reply back into Anthropic SSE events (`message_start` →
    `content_block_delta` → `message_stop`). This is all automatic.

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
