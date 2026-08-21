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

By default it binds `127.0.0.1:11445` with **unified model routing**: request any model from
`alcf-proxy models` and the proxy resolves which cluster (Sophia / Metis / Minerva) serves it,
failing over automatically when a cluster is down — no per-cluster setup. Override basics at launch:

```bash
alcf-proxy serve --port 8080
```

## 3. Check it's healthy

In another terminal:

```bash
curl -s http://localhost:11445/health
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

!!! tip "Any model id just works"
    Model ids differ per cluster (`openai/gpt-oss-120b` on sophia vs `gpt-oss-120b` on metis), but
    unified routing resolves either form and remaps automatically on failover. Just pick anything
    from `alcf-proxy models`.
