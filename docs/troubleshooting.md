# Troubleshooting

## Response ended with finish reason "length" (truncated / empty answer)

`gpt-oss` is a **reasoning model**: it emits reasoning tokens *before* the answer, and those count
against `max_tokens`. If a client (e.g. CherryStudio) sets a small `max_tokens`, reasoning can
consume the whole budget and the answer is cut off — you see `finish_reason: "length"`, often with
empty content.

alcf-proxy mitigates this automatically: when a request **omits** `max_tokens` / `reasoning_effort`,
the proxy injects generous defaults (`max_tokens=128000`, `reasoning_effort=high`). So the simplest
fix is to **not set a small `max_tokens` in your client** — leave it unset and let the proxy default
apply.

If your client forces a small `max_tokens`, raise it (≥ 4096, ideally much more) or lower
`reasoning_effort` to `low`/`medium` in the client so the answer fits. Note: an **explicit**
client value is always respected — the proxy only fills in defaults when the field is missing.

## "We're currently experiencing high demand" (Codex) / empty replies

Almost always the upstream ALCF cluster is unavailable, not real demand. Check:

```bash
alcf-proxy health
curl -s http://localhost:<PORT>/health
```

- If `active_endpoint` shows a cluster that's down, failover should move to the next one on the next
  request. If **all** endpoints are down you'll get a clean `502` from the proxy.
- Verify the proxy itself is authenticated: `alcf-proxy auth status`.

## `alcf-proxy: refusing to bind non-loopback host`

You passed `--host 0.0.0.0` (or similar) without an inbound key. Set one:

```bash
export ALCF_PROXY_API_KEY="strong-secret"
alcf-proxy serve --host 0.0.0.0
```

Clients must then send `Authorization: Bearer strong-secret`. See
[Security](configuration.md#security-binding-beyond-localhost).

## 401 "Permission denied from internal policies" (worked yesterday, 401 today)

ALCF's **30-day high-assurance policy**: the gateway requires a fresh login every ~30 days, even
while your access token still looks valid locally. The proxy surfaces this as a `502` whose error
text starts with "ALCF session expired (30-day re-authentication policy)". Fix:

1. Logout at [app.globus.org/logout](https://app.globus.org/logout)
2. `alcf-proxy auth login`

See [Authentication](authentication.md#30-day-re-authentication-policy).

## 400 "Model ... is not served by any ALCF cluster"

Unified routing couldn't find the requested model in the live catalog. Run `alcf-proxy models` and
use one of the listed ids (any cluster's id works — routing is automatic). If the model *should*
exist, the catalog cache refreshes within ~10 minutes, or restart the proxy.

## Auth: "Failed to obtain an ALCF token"

Your login expired or never happened. Re-authenticate:

```bash
alcf-proxy auth login
alcf-proxy auth status
```

On a headless machine, see the [headless login notes](authentication.md#platform-specific-login).

## Wrong model id / 400 from upstream

Since v0.2.0 this is mostly a non-issue: unified routing accepts **either** form of a model id
(`openai/gpt-oss-120b` or `gpt-oss-120b`) and remaps it per cluster automatically. If you still get
a 400, the model isn't in the current catalog — run `alcf-proxy models`. Note: with an explicit
`endpoints:` override in config, routing is bypassed and the chain's pinned ids are used as-is.

## Port already in use

Another process (or a stale proxy) holds the port. Find your configured port with
`alcf-proxy config show` (or check your `.env`), then:

=== "Linux / macOS"

    ```bash
    ss -tlnp | grep <PORT>     # find the pid
    kill <pid>                 # or choose another port
    alcf-proxy serve --port <OTHER_PORT>
    ```

=== "Windows (PowerShell)"

    ```powershell
    Get-NetTCPConnection -LocalPort <PORT> | Select-Object OwningProcess
    Stop-Process -Id <pid>
    alcf-proxy serve --port <OTHER_PORT>
    ```

## Cold start is slow

An idle model's first request can take a while to spin up (ALCF returns a retryable
`503 "online but not ready"`). The proxy retries briefly; just wait for the first token. Subsequent
requests are fast.

## Coexisting with argo-proxy

Run alcf-proxy on a **different port** than argo-proxy (or any other local proxy) so they don't
collide — set your own port in `.env` (`ALCF_PROXY_PORT=...`, see `.env.example`) or `--port`. They
are independent; configuring one never touches the other.

## Still stuck?

Open an issue at [github.com/cshjin/alcf-proxy/issues](https://github.com/cshjin/alcf-proxy/issues)
with your `alcf-proxy health` output and the client + command you ran.
