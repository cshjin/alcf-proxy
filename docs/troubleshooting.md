# Troubleshooting

## "We're currently experiencing high demand" (Codex) / empty replies

Almost always the upstream ALCF cluster is unavailable, not real demand. Check:

```bash
alcf-proxy health
curl -s http://localhost:11445/health
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

## Auth: "Failed to obtain an ALCF token"

Your login expired or never happened. Re-authenticate:

```bash
alcf-proxy auth login
alcf-proxy auth status
```

On a headless machine, see the [headless login notes](authentication.md#platform-specific-login).

## Wrong model id / 400 from upstream

Model ids differ per cluster:

- `sophia/vllm` → `openai/gpt-oss-120b`
- `metis/api` → `gpt-oss-120b`

List exact ids:

```bash
alcf-proxy models
```

If you pinned a model in your CLI for a cluster that failed over, the id may no longer match. Prefer
letting the proxy use its `default_model`, or pin the id for the endpoint you actually target.

## Port already in use

Another process (or a stale proxy) holds the port:

=== "Linux / macOS"

    ```bash
    ss -tlnp | grep 11445     # find the pid
    kill <pid>                # or choose another port
    alcf-proxy serve --port 11500
    ```

=== "Windows (PowerShell)"

    ```powershell
    Get-NetTCPConnection -LocalPort 11445 | Select-Object OwningProcess
    Stop-Process -Id <pid>
    alcf-proxy serve --port 11500
    ```

## Cold start is slow

An idle model's first request can take a while to spin up (ALCF returns a retryable
`503 "online but not ready"`). The proxy retries briefly; just wait for the first token. Subsequent
requests are fast.

## Coexisting with argo-proxy

argo-proxy typically runs on `localhost:11444`. alcf-proxy defaults to `11445`, so they don't
collide. They are independent; configuring one never touches the other.

## Still stuck?

Open an issue at [github.com/cshjin/alcf-proxy/issues](https://github.com/cshjin/alcf-proxy/issues)
with your `alcf-proxy health` output and the client + command you ran.
