# Quickstart

This walks you from zero to a working chat request through the proxy.

## 1. Install & log in

```bash
pip install alcf-proxy
alcf-proxy auth login      # one-time, opens a browser
```

## 2. Pick a port & start the proxy

alcf-proxy ships with **no built-in default port**. The first time you run `serve` with none
configured, it asks interactively (pre-filled with a suggested port — just press Enter to accept it)
and remembers your answer for next time:

```bash
alcf-proxy serve
```

```text
alcf-proxy: no port configured yet. (Set ALCF_PROXY_PORT in .env — see .env.example — to skip this
prompt next time.)
Port to listen on [52227]:
alcf-proxy: saved ALCF_PROXY_PORT=52227 to /…/alcf-proxy/.env (future runs won't ask again).
alcf-proxy serving on http://127.0.0.1:52227 (sophia/vllm)
  -> check it's up:  curl http://127.0.0.1:52227/health
```

Prefer to set it up front instead of being asked? Copy the template and edit it:

```bash
cp .env.example .env
$EDITOR .env               # uncomment ALCF_PROXY_PORT=... and set a free port
```

Either way, `.env` is gitignored, so your port never ends up in a commit or a shared `config.yaml`.
The rest of the docs write `<PORT>` for whatever you chose (or passed via `--port`).

By default it binds `127.0.0.1` with **unified model routing**: request any model from
`alcf-proxy models` and the proxy resolves which cluster (Sophia / Metis / Minerva) serves it,
failing over automatically when a cluster is down — no per-cluster setup. Override basics at launch:

```bash
alcf-proxy serve --port 8080
```

## 3. Check it's healthy

In another terminal:

```bash
curl -s http://localhost:<PORT>/health
```

```json
{"status":"ok","routing":"unified","token_hours_left":45.7,"cluster":"sophia","framework":"vllm",
 "active_endpoint":{"cluster":"sophia","framework":"vllm","model":"openai/gpt-oss-120b"}, "...":"..."}
```

List the models ALCF is serving:

```bash
alcf-proxy models
```

## 4. Send a chat request

The proxy exposes standard OpenAI endpoints. Any dummy API key works (the proxy injects the real
ALCF token):

=== "curl (chat/completions)"

    ```bash
    curl -s http://localhost:<PORT>/v1/chat/completions \
      -H "Content-Type: application/json" \
      -H "Authorization: Bearer dummy" \
      -d '{
        "model": "openai/gpt-oss-120b",
        "messages": [{"role": "user", "content": "say hello in 3 words"}],
        "stream": true
      }'
    ```

=== "Python (openai SDK)"

    ```python
    from openai import OpenAI

    client = OpenAI(base_url="http://localhost:<PORT>/v1", api_key="dummy")
    resp = client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[{"role": "user", "content": "say hello in 3 words"}],
        stream=True,
    )
    for chunk in resp:
        print(chunk.choices[0].delta.content or "", end="")
    ```

## 5. Point a coding CLI at it

That's the real use case — see [Connect a CLI](clients/index.md) for
[Codex](clients/codex.md), [Claude Code](clients/claude-code.md),
[OpenCode](clients/opencode.md), and [Aider / OpenAI SDK](clients/openai-compatible.md).

!!! tip "Any model id just works"
    Model ids differ per cluster (`openai/gpt-oss-120b` on sophia vs `gpt-oss-120b` on metis), but
    unified routing resolves either form and remaps automatically on failover. Just pick anything
    from `alcf-proxy models`.
