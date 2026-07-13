# Codex CLI

[Codex](https://developers.openai.com/codex) speaks the OpenAI **Responses** API, which alcf-proxy
serves at `/v1/responses`.

## 1. Make sure the proxy is running

```bash
alcf-proxy serve        # http://localhost:11445
```

## 2. Add a model provider to Codex config

Codex reads `$CODEX_HOME/config.toml` (defaults to `~/.codex/config.toml`). Add an ALCF provider:

```toml
[model_providers.alcf]
name = "ALCF (via alcf-proxy)"
base_url = "http://localhost:11445/v1"
wire_api = "responses"
# No API key needed — alcf-proxy injects the real ALCF token.
# If your Codex version requires an env key, point it at a dummy value (see below).

[profiles.alcf]
model = "openai/gpt-oss-120b"
model_provider = "alcf"
```

Launch Codex with that profile:

```bash
codex --profile alcf
```

Or set it as the default by putting `model_provider = "alcf"` and `model = "openai/gpt-oss-120b"` at
the top level of `config.toml`.

!!! warning "Codex ≥ 0.142 quirks (handled for you)"
    Newer Codex removed `wire_api = "chat"` (only `"responses"` is accepted), always streams, and
    stores profiles as separate files. alcf-proxy is built around exactly this: it accepts Codex's
    streaming Responses request and translates it to ALCF's streaming chat upstream. Just use
    `wire_api = "responses"` as shown.

## Cross-platform: locating `config.toml`

=== "Linux / macOS"

    ```bash
    # default
    ~/.codex/config.toml
    # if you set CODEX_HOME (some setups use $SCRATCH/.codex on HPC):
    echo $CODEX_HOME
    ```

=== "Windows (PowerShell)"

    ```powershell
    # default
    $HOME\.codex\config.toml
    # if CODEX_HOME is set:
    echo $env:CODEX_HOME
    ```

Edit the file at that location.

## If Codex insists on an API key

Some builds require an `env_key`. Set a dummy value — the proxy ignores it and injects the real
token:

```toml
[model_providers.alcf]
name = "ALCF (via alcf-proxy)"
base_url = "http://localhost:11445/v1"
wire_api = "responses"
env_key = "ALCF_DUMMY_KEY"
```

=== "Linux / macOS"

    ```bash
    export ALCF_DUMMY_KEY=dummy
    codex --profile alcf
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:ALCF_DUMMY_KEY = "dummy"
    codex --profile alcf
    ```

## Don't disturb an existing argo setup

If you already use argo-proxy on `localhost:11444` as your default Codex provider, keep it — just add
`[model_providers.alcf]` alongside it and select it with `--profile alcf` (or the in-console `/model`
switch). alcf-proxy runs on a different port (11445) and doesn't touch your argo config.

## Troubleshooting

- **"We're currently experiencing high demand" / reconnect loop** — usually the upstream cluster is
  down; alcf-proxy fails over automatically, but check `alcf-proxy health`. See
  [Troubleshooting](../troubleshooting.md).
- **Wrong model id** — on metis use `gpt-oss-120b` (no `openai/` prefix). Run `alcf-proxy models`.
