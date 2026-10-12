# Proxy configuration

alcf-proxy is configured by (in order of precedence):

1. **CLI flags** (`--port`, `--host`, `--cluster`, `--framework`, `--model`)
2. **Environment variables** (`ALCF_PROXY_*`), including a local `.env` file (see below)
3. **YAML config file**
4. **Built-in defaults** — note there is **no built-in default port**; see below.

## Port: `.env` file (recommended)

alcf-proxy does not ship with a hardcoded default port, so it's never silently baked into a commit,
a shared `config.yaml`, or a screenshot.

**Easiest:** just run `alcf-proxy serve`. If no port is configured anywhere and you're at an
interactive terminal, it asks once (with a pre-filled suggestion — press Enter to accept) and writes
the answer to `.env` in the platform user-config dir, so you're never asked again:

```text
Port to listen on [52227]:
alcf-proxy: saved ALCF_PROXY_PORT=52227 to /…/alcf-proxy/.env (future runs won't ask again).
```

Running non-interactively (a service unit, CI, a container)? There's nothing to prompt, so set it up
front instead:

```bash
cp .env.example .env
$EDITOR .env    # uncomment ALCF_PROXY_PORT=... and set a free port
```

`.env` is loaded automatically (searched the same way as `config.yaml`: `./.env`, then the platform
user-config dir) and is listed in `.gitignore`, so it's never committed. Everything in it is just a
regular `ALCF_PROXY_*` environment variable — see the table below for the full list.

## Config file

Search order (first found wins):

1. `./config.yaml` (current directory)
2. Platform user-config dir:
    - Linux: `~/.config/alcf-proxy/config.yaml`
    - macOS: `~/Library/Application Support/alcf-proxy/config.yaml`
    - Windows: `%APPDATA%\alcf-proxy\config.yaml`

Generate a starter file:

```bash
alcf-proxy config init
```

Print the effective config (with everything merged):

```bash
alcf-proxy config show
```

### Example `config.yaml`

```yaml
host: 127.0.0.1
# port: 52227               # optional — prefer setting ALCF_PROXY_PORT in .env instead (see above)
cluster: sophia            # primary cluster
framework: vllm            # primary framework
default_model: openai/gpt-oss-120b
verbose: false

# Optional: explicit ordered failover list (see Endpoints & failover).
# endpoints:
#   - {cluster: sophia, framework: vllm, model: openai/gpt-oss-120b}
#   - {cluster: metis,  framework: api,  model: gpt-oss-120b}
```

## Environment variables

Every top-level key has an `ALCF_PROXY_<KEY>` override:

| Variable | Effect |
|----------|--------|
| `ALCF_PROXY_HOST` | bind host |
| `ALCF_PROXY_PORT` | bind port |
| `ALCF_PROXY_CLUSTER` | primary cluster |
| `ALCF_PROXY_FRAMEWORK` | primary framework |
| `ALCF_PROXY_DEFAULT_MODEL` | default model id |
| `ALCF_PROXY_VERBOSE` | `true`/`false` verbose logging |
| `ALCF_PROXY_CLUSTER_PRIORITY` | comma-separated cluster order for unified routing (e.g. `metis,sophia`) |
| `ALCF_PROXY_API_KEY` | require this bearer key from clients (needed for non-loopback bind) |

Any of these can be exported directly, or (preferred, so you don't have to re-export every shell
session) put in `.env` as shown above.

=== "Linux / macOS"

    ```bash
    export ALCF_PROXY_PORT=8080
    alcf-proxy serve
    ```

=== "Windows (PowerShell)"

    ```powershell
    $env:ALCF_PROXY_PORT = "8080"
    alcf-proxy serve
    ```

## Security: binding beyond localhost

By default the proxy binds `127.0.0.1` (localhost only), which is correct for a single-user machine —
the proxy injects **your** ALCF token into every request it forwards.

If you bind a non-loopback host (`--host 0.0.0.0`), alcf-proxy **refuses to start** unless you set an
inbound API key, so random hosts on your network can't spend your token:

```bash
export ALCF_PROXY_API_KEY="choose-a-strong-secret"
alcf-proxy serve --host 0.0.0.0 --port 8080
```

Clients must then send `Authorization: Bearer choose-a-strong-secret`. Since v0.2.0 this is
**enforced** on every route except `/health`: requests with a missing or wrong key get `401`.
(When `ALCF_PROXY_API_KEY` is unset and the bind is loopback, any dummy key is accepted as before.)

Next: [Endpoints & failover](endpoints.md).
