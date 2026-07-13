# Endpoints & failover

ALCF serves models from multiple clusters/frameworks (e.g. `sophia/vllm`, `metis/api`). Clusters go
under maintenance from time to time. alcf-proxy handles this with an ordered **endpoint list** and
automatic **failover**.

## How it works

An endpoint is a triple: `{cluster, framework, model}`. The model id is part of the endpoint because
**it differs per cluster**:

| Cluster / framework | Model id |
|---------------------|----------|
| `sophia/vllm` | `openai/gpt-oss-120b` |
| `metis/api` | `gpt-oss-120b` (no `openai/` prefix) |

The proxy tries endpoints in order. When a cluster returns `503` / "under maintenance" (or a
cold-start never becomes ready), it advances to the next endpoint, **remapping the model id**, and
then **sticks** to the working endpoint so it doesn't re-probe the dead one on every request.

```text
request ──► sophia/vllm  (503 maintenance)
        ──► metis/api    (200)  ✓  → stick here
```

## Default failover chain

If you don't configure endpoints explicitly, the proxy synthesizes:

1. your primary (`cluster` / `framework` / `default_model` from config)
2. the built-in fallback chain (`sophia/vllm/openai/gpt-oss-120b` → `metis/api/gpt-oss-120b`),
   de-duplicated against your primary.

## Explicit endpoint list

For full control, set `endpoints:` in `config.yaml` (used verbatim, in order):

```yaml
endpoints:
  - {cluster: metis,  framework: api,  model: gpt-oss-120b}
  - {cluster: sophia, framework: vllm, model: openai/gpt-oss-120b}
```

## Observing failover

`/health` and `alcf-proxy health` report the currently active endpoint and the full list:

```bash
curl -s http://localhost:11445/health
```

```json
{
  "status": "ok",
  "cluster": "metis",
  "framework": "api",
  "active_endpoint": {"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"},
  "endpoints": [
    {"cluster": "sophia", "framework": "vllm", "model": "openai/gpt-oss-120b"},
    {"cluster": "metis",  "framework": "api",  "model": "gpt-oss-120b"}
  ]
}
```

!!! info "Maintenance vs cold start"
    A cold-started (idle) model returns a retryable `503 "online but not ready"` — the proxy retries
    briefly. A cluster `503 "under maintenance"` is treated as down and triggers failover
    immediately.
