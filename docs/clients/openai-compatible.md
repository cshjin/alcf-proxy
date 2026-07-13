# Aider & OpenAI SDK

Anything that speaks the OpenAI **Chat Completions** API works against alcf-proxy's
`/v1/chat/completions` endpoint. Set the base URL to the proxy and use any dummy key.

## Aider

[Aider](https://aider.chat) supports OpenAI-compatible endpoints via `--openai-api-base` or env vars.

```bash
alcf-proxy serve    # keep running
```

=== "Linux / macOS"

    ```bash
    export OPENAI_API_BASE="http://localhost:11445/v1"
    export OPENAI_API_KEY="dummy"
    aider --model openai/openai/gpt-oss-120b
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:OPENAI_API_BASE = "http://localhost:11445/v1"
    $env:OPENAI_API_KEY = "dummy"
    aider --model openai/openai/gpt-oss-120b
    ```

!!! note "Aider model prefix"
    Aider routes OpenAI-compatible models through LiteLLM, which expects an `openai/` routing prefix.
    Combined with ALCF's own `openai/gpt-oss-120b` id, that becomes `openai/openai/gpt-oss-120b`. On
    metis the id is `gpt-oss-120b`, so use `openai/gpt-oss-120b`.

## OpenAI Python SDK

```python
from openai import OpenAI

client = OpenAI(base_url="http://localhost:11445/v1", api_key="dummy")

# non-streaming
resp = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Write a haiku about supercomputers."}],
)
print(resp.choices[0].message.content)

# streaming
stream = client.chat.completions.create(
    model="openai/gpt-oss-120b",
    messages=[{"role": "user", "content": "Count to five."}],
    stream=True,
)
for chunk in stream:
    print(chunk.choices[0].delta.content or "", end="", flush=True)
```

## Node / other SDKs

Any OpenAI SDK accepts a custom base URL. For example, JS:

```js
import OpenAI from "openai";
const client = new OpenAI({ baseURL: "http://localhost:11445/v1", apiKey: "dummy" });
```

## Tips

- **Base URL** always ends in `/v1` for chat-completions clients.
- **Dummy key** — the proxy injects the real ALCF token; the key you pass is ignored (unless you set
  `ALCF_PROXY_API_KEY` for a networked deployment).
- **Model ids** — `alcf-proxy models` lists exact ids per cluster.
