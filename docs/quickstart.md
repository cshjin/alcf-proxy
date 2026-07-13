# Quickstart

This walks you from zero to a working chat request through the proxy.

## 1. Install & log in

```bash
pip install alcf-proxy
alcf-proxy auth login      # one-time, opens a browser
```

## 2. Start the proxy

```bash
alcf-proxy serve
```

```text
alcf-proxy serving on http://127.0.0.1:11445 (sophia/vllm)
```

By default it binds `127.0.0.1:11445` with primary cluster `sophia/vllm` and default model
`openai/gpt-oss-120b`, and will fail over to `metis/api` if sophia is down. Override at launch:

```bash
alcf-proxy serve --port 8080 --cluster metis --framework api --model gpt-oss-120b
```

## 3. Check it's healthy

In another terminal:

```bash
curl -s http://localhost:11445/health
```

```json
{"status":"ok","token_hours_left":45.7,"cluster":"sophia","framework":"vllm",
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
    curl -s http://localhost:11445/v1/chat/completions \
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

    client = OpenAI(base_url="http://localhost:11445/v1", api_key="dummy")
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

!!! tip "Model ids differ per cluster"
    On `sophia/vllm` the model is `openai/gpt-oss-120b`; on `metis/api` it is `gpt-oss-120b` (no
    `openai/` prefix). When failover switches clusters, the proxy remaps the model for you — but if
    you pin a model in your CLI, use the id for the cluster you're targeting. Run `alcf-proxy models`
    to see exact ids.
