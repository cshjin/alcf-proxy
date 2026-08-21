# Endpoints, unified routing & failover

ALCF serves models from multiple clusters/frameworks (`sophia/vllm`, `metis/api`, `minerva/api`).
Model ids differ per cluster, clusters go under maintenance, and new clusters appear. alcf-proxy
hides all of that behind **unified model routing**: clients just name a model; the proxy figures
out where to send it.

## Unified model routing (default since v0.2.0)

On demand, the proxy pulls the gateway's live catalog (`list-endpoints`, cached ~10 min) and builds
a routing table: **model → ordered list of clusters that serve it**. For every request:

1. **Exact id match** first — e.g. `openai/gpt-oss-120b`.
2. **Basename match** second — `gpt-oss-120b` also finds sophia's `openai/gpt-oss-120b` (ids
   differ per cluster; the proxy remaps to each cluster's local id automatically).
3. Candidates are ordered by `cluster_priority` (default `sophia, metis, minerva`); the first
   working cluster is used and remembered (sticky), with automatic failover to the next on
   503/maintenance.

So you can point your CLI at **any model from `alcf-proxy models`** — no cluster/framework
configuration, no config edits when you switch models:

```bash
# all of these just work, no proxy reconfiguration:
#   model = openai/gpt-oss-120b   -> sophia (falls back to metis)
#   model = gpt-oss-120b          -> same model, resolved across clusters
#   model = nemotron-3-ultra      -> minerva
#   model = meta-llama/Llama-3.3-70B-Instruct -> sophia
```

Unknown model → clean `400` with a hint to run `alcf-proxy models`. If the catalog itself is
temporarily unreachable, the proxy falls back to the configured failover chain below (and keeps
serving a stale cached table rather than failing; failed refreshes are backoff-throttled so a slow
catalog endpoint never stalls requests).

!!! note "Behavior change vs v0.1.x"
    v0.1.x silently remapped *any* requested model id to the configured chain's model. v0.2.0
    rejects ids that aren't in the live catalog with a `400`. If you relied on arbitrary model
    names, pin an explicit `endpoints:` list (which bypasses the router and restores the old
    remapping behavior).

### `/v1/models`

Returns the **unified pool** in standard OpenAI shape, so GUI clients (CherryStudio etc.) can list
and pick models directly:

```json
{"object": "list", "data": [
  {"id": "openai/gpt-oss-120b", "object": "model", "owned_by": "sophia/vllm"},
  {"id": "gpt-oss-120b", "object": "model", "owned_by": "metis/api"},
  {"id": "nemotron-3-ultra", "object": "model", "owned_by": "minerva/api"}, "..."
]}
```

## Cluster priority

```yaml
# config.yaml
cluster_priority: [sophia, metis, minerva]   # default
```

Or env: `ALCF_PROXY_CLUSTER_PRIORITY="metis,sophia"`.

## The failover chain (fallback / override)

The pre-v0.2.0 mechanism still exists for two purposes:

1. **Fallback** when the live catalog is unavailable. Default chain:

    | # | Cluster / framework | Model |
    |---|---------------------|-------|
    | 1 | `sophia/vllm` | `openai/gpt-oss-120b` |
    | 2 | `metis/api` | `gpt-oss-120b` |
    | 3 | `minerva/api` | `gpt-oss-120b` |

2. **Explicit override**: pin `endpoints:` in `config.yaml` and the router is bypassed entirely
   (every request goes through your chain, in order, regardless of the requested model):

    ```yaml
    endpoints:
      - {cluster: metis,  framework: api,  model: gpt-oss-120b}
      - {cluster: sophia, framework: vllm, model: openai/gpt-oss-120b}
    ```

## Observing routing

`/health` reports the routing mode, the fallback chain, and its currently active endpoint:

```bash
curl -s http://localhost:11445/health
```

```json
{
  "status": "ok",
  "routing": "unified",
  "active_endpoint": {"cluster": "sophia", "framework": "vllm", "model": "openai/gpt-oss-120b"},
  "endpoints": ["..."]
}
```

!!! info "Maintenance vs cold start"
    A cold-started (idle) model returns a retryable `503 "online but not ready"` — the proxy
    retries briefly. A cluster `503 "under maintenance"` is treated as down and triggers failover
    immediately.
