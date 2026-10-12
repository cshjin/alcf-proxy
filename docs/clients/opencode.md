# OpenCode

[OpenCode](https://opencode.ai) is an OpenAI-compatible coding CLI. Point it at alcf-proxy's
`/v1/chat/completions` endpoint with a custom provider.

## 1. Start the proxy

```bash
alcf-proxy serve        # http://localhost:11445
```

## 2. Configure an OpenAI-compatible provider

OpenCode is configured via `opencode.jsonc` (project root) or `~/.config/opencode/opencode.jsonc`. Add
a custom provider pointing to the proxy:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "providers": {
    "alcf-proxy": {
      "name": "alcf-proxy",
      "package": "@opencode/ai/providers/openai-compatible",
      "settings": {
        "baseURL": "http://localhost:11445/v1"
      },
      "models": {
        "inkling-bf16": {
          "modelID": "inkling-bf16",
          "name": "inkling-bf16"
        },
        "gpt-oss-120b": {
          "modelID": "gpt-oss-120b",
          "name": "gpt-oss-120b"
        }
      }
    }
  }
}
```

Then run OpenCode with the model:
```bash
opencode run --model alcf-proxy/inkling-bf16 "Your prompt here"
```

## Cross-platform config location

=== "Linux"

    `~/.config/opencode/opencode.json` — or `opencode.json` in your project root.

=== "macOS"

    `~/.config/opencode/opencode.json` — or `opencode.json` in your project root.

=== "Windows"

    `%USERPROFILE%\.config\opencode\opencode.json` — or `opencode.json` in your project root.

!!! tip "Environment variable alternative"
    Many OpenAI-compatible tools also accept `OPENAI_BASE_URL` / `OPENAI_API_KEY`:

    === "Linux / macOS"
        ```bash
        export OPENAI_BASE_URL="http://localhost:11445/v1"
        export OPENAI_API_KEY="dummy"
        ```
    === "Windows (PowerShell)"
        ```powershell
        $env:OPENAI_BASE_URL = "http://localhost:11445/v1"
        $env:OPENAI_API_KEY = "dummy"
        ```

## Model ids

Use the id for the active cluster: `openai/gpt-oss-120b` (sophia) or `gpt-oss-120b` (metis). Run
`alcf-proxy models` to list them.
