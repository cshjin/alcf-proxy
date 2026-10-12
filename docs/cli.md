# CLI reference

```text
alcf-proxy <command> [options]
```

## `serve`

Start the translating gateway (foreground, resident).

```bash
alcf-proxy serve [--host HOST] [--port PORT] [--cluster C] [--framework F] [--model M] [--config PATH]
```

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `127.0.0.1` | Bind host. Non-loopback requires `ALCF_PROXY_API_KEY`. |
| `--port` | *(none)* | Bind port. No built-in default — set `ALCF_PROXY_PORT` in `.env` (see [Configuration](configuration.md)), `port:` in `config.yaml`, or pass this flag. If none of those are set and you're at an interactive terminal, `serve` prompts for one (and saves it to `.env`) instead of erroring. |
| `--cluster` | `sophia` | Primary cluster. |
| `--framework` | `vllm` | Primary framework. |
| `--model` | `openai/gpt-oss-120b` | Default model id. |
| `--config` | (search paths) | Explicit config file path. |

Exposes: `POST /v1/chat/completions`, `POST /v1/responses`, `POST /v1/messages`,
`GET /v1/models`, `GET /health`.

## `models`

List models currently served by ALCF (across clusters/frameworks).

```bash
alcf-proxy models          # human-readable
alcf-proxy models --json   # machine-readable
```

## `health`

Print token status (JSON), including hours until expiry.

```bash
alcf-proxy health
```

## `auth`

Manage Globus authentication (see [Authentication](authentication.md)).

```bash
alcf-proxy auth login      # one-time interactive browser login
alcf-proxy auth status     # authenticated? token path + hours left
```

## `config`

Manage configuration (see [Proxy config](configuration.md)).

```bash
alcf-proxy config init     # write a starter config.yaml
alcf-proxy config show     # print the effective (merged) config
```

## HTTP endpoints (when serving)

| Method & path | Purpose |
|---------------|---------|
| `POST /v1/chat/completions` | OpenAI Chat (Aider, OpenCode, OpenAI SDK) |
| `POST /v1/responses` | OpenAI Responses (Codex) |
| `POST /v1/messages` | Anthropic Messages (Claude Code) |
| `GET /v1/models` | model list |
| `GET /health` | status, active endpoint, token hours left |
