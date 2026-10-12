# Upgrading

## v0.3.0 → v0.3.1

```bash
pip install -U alcf-proxy
```

### New in v0.3.1

- **No more hardcoded default port**: `port` has no built-in value anymore. Copy `.env.example` to
  `.env` and set `ALCF_PROXY_PORT` (or use `--port` / `port:` in `config.yaml` as before). `.env` is
  gitignored, so your port is never baked into a commit or a shared config file. Running
  `alcf-proxy serve` with no port configured anywhere now exits with a clear message instead of
  silently binding `11445`.
  *Affected:* anyone relying on the old implicit default of `11445` with zero configuration.
  *Fix:* `cp .env.example .env` once, set a port, done.

## v0.2.x → v0.3.0

Upgrade via pip:

```bash
pip install -U alcf-proxy
# then restart the proxy:
alcf-proxy serve
```

### New in v0.3.0

- **Claude Code & Anthropic Messages streaming**: SSE events now emit standard `event: {type}` headers and clean termination, fully compatible with `@anthropic-ai/sdk`.
- **Non-streaming response fallback**: automatically aggregates streaming chunks into complete JSON responses when `stream: false`, ensuring resilience on client retries.
- **Model context window syntax**: automatically strips `[1m]`, `[200k]`, etc. from model names (e.g. `inkling-bf16[1m]` -> `inkling-bf16`).
- **Minerva `inkling-bf16` support**: full support for 1M context window and thinking/reasoning deltas on Minerva.
- **`alcf-tokens` compatibility**: automatically detects and shares existing login tokens created by the official `alcf-tokens` CLI (`7f3e61f5-...`).
- **`unknown_model_fallback` option**: permits automatic fallback to a designated model when clients request unrecognized models.
- **Upgraded `llm-rosetta`** to `>=0.13.0`.

## v0.1.x → v0.2.0

**TL;DR: no migration work for typical setups.** Client configs (Codex / Claude Code / OpenCode /
Aider), your `config.yaml`, and your Globus login all keep working as-is. Upgrade is just:

```bash
pip install -U alcf-proxy
# then restart the proxy (a running process does not hot-reload):
alcf-proxy serve
```

### What stays compatible

- **Client setup unchanged** — same base URL (`http://localhost:<PORT>/v1`), same dummy API key,
  same endpoints (`/v1/chat/completions`, `/v1/responses`, `/v1/messages`).
- **`config.yaml` unchanged** — every v0.1.x key is still valid. The new `cluster_priority` key is
  optional (defaults to `[sophia, metis, minerva]`). An existing explicit `endpoints:` list behaves
  exactly as before (and now explicitly bypasses the new router).
- **Auth unchanged** — same token storage; upgrading does not require a new login. (Separately,
  ALCF now forces a re-login every ~30 days — see
  [Authentication](authentication.md#30-day-re-authentication-policy).)
- **CLI unchanged** — `serve` / `models` / `health` / `config` / `auth`, same flags. The
  human-readable output of `alcf-proxy models` is unchanged.

### Behavior changes to be aware of

1. **Unknown models now return `400`** (previously: any requested model id was *silently remapped*
   to the configured chain's model — asking for Llama could quietly get you gpt-oss).
   With unified routing, the model you ask for is the model you get; ids not in the live catalog
   are rejected with a hint.
   *Affected:* clients configured with arbitrary/stale model names.
   *Fix:* use a real id from `alcf-proxy models` (any cluster's spelling works), or pin an
   explicit `endpoints:` list in `config.yaml` to restore the old remapping behavior.

2. **`/v1/models` response shape is now standard OpenAI** —
   `{"object": "list", "data": [{"id": ..., "object": "model", "owned_by": "cluster/fw"}]}`
   instead of the old `{"data": ["cluster/fw: model", ...]}` string list.
   *Affected:* only scripts that parsed the old strings. GUI clients (CherryStudio etc.) now work
   *better* — they can list and pick models directly.
   *Fix:* read `data[].id`.

3. **`ALCF_PROXY_API_KEY` is now enforced** on every route except `/health` (in v0.1.x it only
   gated non-loopback binding and was never checked inbound).
   *Affected:* setups that set the env var but whose clients send a dummy key — those now get `401`.
   *Fix:* have clients send `Authorization: Bearer <your ALCF_PROXY_API_KEY>`, or unset the var for
   loopback-only use (default behavior unchanged: no key set → any dummy key accepted).

### New in v0.2.0 (no action needed, just nicer)

- **Unified model routing**: request any model id from `alcf-proxy models`; the proxy resolves the
  hosting cluster, remaps per-cluster id spellings, and fails over across clusters automatically.
- **Three-cluster failover for gpt-oss-120b** (sophia, metis, and the new Minerva all serve it).
- Clear guidance when ALCF's 30-day re-auth policy trips (instead of a raw 401).
