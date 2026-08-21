# Available models

alcf-proxy forwards to whatever models ALCF serves. This page mirrors ALCF's
[official catalog](https://docs.alcf.anl.gov/services/inference-endpoints/); run `alcf-proxy models`
for the live, authoritative list (ids differ per cluster).

!!! tip "Unified routing (v0.2.0)"
    You can request **any** model id below directly — the proxy resolves which cluster serves it
    (and fails over between clusters hosting the same model) automatically. No per-cluster
    configuration. See [Endpoints & failover](endpoints.md).

!!! tip "Recommended: ⭐ `openai/gpt-oss-120b`"
    `openai/gpt-oss-120b` is the recommended default for coding CLIs — it's a large reasoning model,
    **always hot** (low latency), supports **tool calling**, **reasoning**, and **batch**, and is
    available on both Sophia (`openai/gpt-oss-120b`) and Metis (`gpt-oss-120b`). It is alcf-proxy's
    built-in default and failover chain.

## Feature legend

| Flag | Meaning |
|:----:|---------|
| **B** | Batch processing enabled |
| **T** | Tool calling enabled |
| **R** | Reasoning enabled |
| **H** | Always hot (kept loaded → low latency) |

## Sophia cluster (`sophia/vllm`)

Base URL: `…/resource_server/sophia/vllm/v1` · Endpoints: chat/completions, responses, messages,
completions, embeddings, batches.

### Chat / language models

| Model | B | T | R | H |
|-------|:-:|:-:|:-:|:-:|
| ⭐ **openai/gpt-oss-120b** | ✅ | ✅ | ✅ | ✅ |
| openai/gpt-oss-20b | ✅ | ✅ | ✅ | ✅ |
| meta-llama/Meta-Llama-3.1-8B-Instruct | ✅ | ✅ | | ✅ |
| meta-llama/Meta-Llama-3.1-70B-Instruct | ✅ | ✅ | | ✅ |
| meta-llama/Meta-Llama-3.1-405B-Instruct | ✅ | ✅ | | |
| meta-llama/Llama-3.3-70B-Instruct | ✅ | ✅ | | |
| meta-llama/Llama-4-Scout-17B-16E-Instruct | ✅ | ✅ | | |
| meta-llama/Llama-4-Maverick-17B-128E-Instruct | | ✅ | | |
| mistralai/Mistral-Large-Instruct-2407 | | | | |
| mistralai/Mixtral-8x22B-Instruct-v0.1 | | | | |
| mistralai/Devstral-2-123B-Instruct-2512 | | | | |
| argonne/AuroraGPT-IT-v4-0125 | ✅ | | | |
| argonne/AuroraGPT-Tulu3-SFT-0125 | ✅ | | | |
| argonne/AuroraGPT-DPO-UFB-0225 | ✅ | | | |
| argonne/AuroraGPT-KTO-UFB-0325 | ✅ | | | |
| google/gemma-3-27b-it | ✅ | ✅ | | |
| google/gemma-4-26B-A4B-it | | ✅ | ✅ | |
| google/gemma-4-31B-it | | ✅ | ✅ | ✅ |
| google/gemma-4-E4B-it | | ✅ | ✅ | ✅ |
| arcee-ai/Trinity-Large-Thinking-W4A16 | | ✅ | ✅ | |
| nvidia/nemotron-3-super-120b | | ✅ | ✅ | |
| mgoin/Nemotron-4-340B-Instruct-hf | | | | |
| AstroMLab/AstroSage-70B-20251009 | | | | |

### Vision language models

| Model | B | T | R | H |
|-------|:-:|:-:|:-:|:-:|
| meta-llama/Llama-3.2-90B-Vision-Instruct | | | | |

### Embedding models

`mistralai/Mistral-7B-Instruct-v0.3-embed`, `Salesforce/SFR-Embedding-Mistral`, and the
`genslm-test/genslm-esmc-*` family (300M/600M, aminoacid/codon variants). Use the `/v1/embeddings`
endpoint directly against ALCF for these.

### Image segmentation

`facebook/sam3` (promptable segmentation) — see ALCF's `alcf-ai` toolkit; not exposed through
alcf-proxy's chat/responses/messages routes.

## Metis cluster (`metis/api`, SambaNova)

Base URL: `…/resource_server/metis/api/v1` · Endpoints: chat/completions only (the proxy still serves responses/messages clients by translating to chat).

| Model | B | T | R | H |
|-------|:-:|:-:|:-:|:-:|
| ⭐ **gpt-oss-120b** | | | | ✅ |
| Mistral-Large-3-675B-Instruct-2512 | | | | ✅ |
| gemma-4-31B-it | | | | ✅ |

!!! note "Metis limitations"
    Batch processing and tool calling are **not** supported on Metis. Model ids on Metis have **no**
    `openai/` prefix (e.g. `gpt-oss-120b`, not `openai/gpt-oss-120b`).

## Minerva cluster (`minerva/api`, NVIDIA B200) — new

Base URL: `…/resource_server/minerva/api/v1` · Endpoints: chat/completions, responses, messages,
completions, embeddings.

| Model | B | T | R | H |
|-------|:-:|:-:|:-:|:-:|
| ⭐ **gpt-oss-120b** | | | | |
| nemotron-3-ultra | | | | ✅ |
| inkling-bf16 | | | | |

(Live catalog 2026-08-21; minerva now serves `gpt-oss-120b` too, so the recommended model gets
**three-cluster failover**. ALCF's published feature flags for minerva currently cover only
`nemotron-3-ultra`.)

## Notes

- Three clusters are currently active (Sophia, Metis, Minerva); ALCF says more systems are coming.
- The catalog changes over time — `alcf-proxy models` and ALCF's
  [official docs](https://docs.alcf.anl.gov/services/inference-endpoints/) are the source of truth.
- Feature flags (B/T/R/H) are ALCF's; alcf-proxy passes tool-calling and reasoning through, so a
  model marked **T**/**R** works for agentic coding CLIs.
