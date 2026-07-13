"""Chat-request sanitizers for ALCF's vLLM backend (applied after translation to chat).

FACT 6: vLLM only accepts tools of type 'function'; codex sends 'namespace'/'web_search'.
FACT 7: assistant message content may be a list of parts; vLLM wants a plain string there.
"""
from __future__ import annotations

_SUPPORTED_TOOL_TYPES = {"function"}


def _flatten_content(content):
    if isinstance(content, list):
        return "".join(
            p.get("text", "")
            for p in content
            if isinstance(p, dict) and p.get("type") in ("text", "output_text", "input_text")
        )
    return content


def sanitize_chat(body: dict) -> dict:
    out = dict(body)
    out["stream"] = True
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
            if isinstance(m, dict) and m.get("role") == "assistant":
                m = dict(m)
                m["content"] = _flatten_content(m.get("content"))
            new.append(m)
        out["messages"] = new
    return out
