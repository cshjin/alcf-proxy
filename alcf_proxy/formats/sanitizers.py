"""Chat-request sanitizers for ALCF backends (applied after translation to chat).

FACT 6: vLLM only accepts tools of type 'function'; codex sends 'namespace'/'web_search'.
FACT 7: message content may be a list of parts (any role). ALCF wants a plain string — metis
(SambaNova) hard-rejects list content with HTTP 422 "Input should be a valid string", and vLLM is
happiest with a string too. So we flatten list-of-parts content to a string for EVERY role.
FACT 8: gpt-oss is a reasoning model — reasoning tokens count against max_tokens, so a small
client-set max_tokens gets fully consumed by reasoning and the answer is truncated
(finish_reason "length"). We inject a large default max_tokens and reasoning_effort when the client
omits them (never overriding an explicit client value). Verified: both accepted on sophia + metis,
and non-reasoning models (e.g. gemma-3-27b-it) ignore reasoning_effort gracefully (HTTP 200).
"""
from __future__ import annotations

_SUPPORTED_TOOL_TYPES = {"function"}

# Defaults injected only when the client omits them.
DEFAULT_MAX_TOKENS = 128000
DEFAULT_REASONING_EFFORT = "high"


def _flatten_content(content):
    if isinstance(content, list):
        return "".join(
            p.get("text", "")
            for p in content
            if isinstance(p, dict) and p.get("type") in ("text", "output_text", "input_text")
        )
    return content


def sanitize_chat(
    body: dict,
    default_max_tokens: int | None = DEFAULT_MAX_TOKENS,
    default_reasoning_effort: str | None = DEFAULT_REASONING_EFFORT,
) -> dict:
    out = dict(body)
    out["stream"] = True
    # Reasoning-model defaults: inject only when the client didn't specify them. Pass None to disable.
    if default_max_tokens is not None and out.get("max_tokens") is None:
        out["max_tokens"] = default_max_tokens
    if default_reasoning_effort is not None and out.get("reasoning_effort") is None:
        out["reasoning_effort"] = default_reasoning_effort
    tools = out.get("tools")
    if isinstance(tools, list):
        kept = [t for t in tools if isinstance(t, dict) and t.get("type") in _SUPPORTED_TOOL_TYPES]
        if kept:
            out["tools"] = kept
        else:
            out.pop("tools", None)
            out.pop("tool_choice", None)
    msgs = out.get("messages")
    if isinstance(msgs, list):
        new = []
        for m in msgs:
            if isinstance(m, dict) and isinstance(m.get("content"), list):
                m = dict(m)
                m["content"] = _flatten_content(m["content"])
            new.append(m)
        out["messages"] = new
    return out
