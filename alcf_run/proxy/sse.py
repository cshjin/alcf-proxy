"""Rebuild a complete (non-streaming) ALCF responses JSON into responses-API SSE events.

ALCF's gateway rejects streaming, but codex requires it. We fetch the full JSON, then synthesize the
SSE event sequence codex expects using llm-rosetta's IR stream events (see _hj FACT 2).

The working path (verified live against llm-rosetta 0.6.12): build a sequence of IR stream events and
feed each to ``OpenAIResponsesConverter.stream_response_to_provider(event, ctx)``, collecting the
returned responses SSE payload dict(s) in order. ``ctx = conv.create_stream_context()``.

Notes discovered empirically:
- IR events are plain TypedDicts. ``FinishEvent.finish_reason`` must be a ``FinishReason`` dict
  (``{"reason": "stop"}``), NOT a bare string — a string raises ``TypeError`` inside the converter.
- ``stream_response_to_provider`` may return a dict, a list of dicts, or None — always normalize.
- Some IR events (finish/usage) map to internal SSE payloads with no ``type`` key; we drop those so
  the emitted stream contains only real responses events. ``StreamEndEvent`` maps to the final
  ``response.completed`` event, which carries ``response.usage.output_tokens``.
"""
import json

from llm_rosetta import OpenAIResponsesConverter
from llm_rosetta.types.ir import stream as S

_conv = OpenAIResponsesConverter()


def _extract(resp: dict):
    """Return (text, reasoning_text, tool_calls, usage) from a complete ALCF response."""
    text_parts, reasoning_parts, tool_calls = [], [], []
    for item in resp.get("output", []) or []:
        itype = item.get("type")
        if itype == "message":
            for c in item.get("content", []) or []:
                if c.get("type") == "output_text":
                    text_parts.append(c.get("text", ""))
        elif itype == "reasoning":
            for c in item.get("content", []) or []:
                if c.get("type") == "reasoning_text":
                    reasoning_parts.append(c.get("text", ""))
        elif itype == "function_call":
            tool_calls.append({
                "id": item.get("id") or item.get("call_id"),
                "call_id": item.get("call_id") or item.get("id"),
                "name": item.get("name"),
                "arguments": item.get("arguments") or "",
            })
    return "".join(text_parts), "".join(reasoning_parts), tool_calls, resp.get("usage") or {}


def _emit(ctx, event) -> list[dict]:
    """Feed one IR event to the converter and return the SSE payload dicts (typed only)."""
    out = _conv.stream_response_to_provider(event, ctx)
    if out is None:
        return []
    items = out if isinstance(out, list) else [out]
    # Drop internal payloads that carry no responses event ``type`` (e.g. finish/usage bookkeeping).
    return [e for e in items if isinstance(e, dict) and e.get("type")]


def response_json_to_sse_events(resp: dict) -> list[dict]:
    """Convert a complete ALCF responses JSON into an ordered list of responses SSE payload dicts.

    The first event is ``response.created`` and the last is ``response.completed`` (whose
    ``response.usage`` mirrors the ALCF usage block).
    """
    text, _reasoning, tool_calls, usage = _extract(resp)
    ctx = _conv.create_stream_context()
    events: list[dict] = []
    events += _emit(ctx, S.StreamStartEvent(
        type="stream_start", response_id=resp.get("id", ""), model=resp.get("model", "")))

    block = 0
    if text:
        events += _emit(ctx, S.ContentBlockStartEvent(
            type="content_block_start", index=block, block_type="text"))
        events += _emit(ctx, S.TextDeltaEvent(type="text_delta", index=block, text=text))
        events += _emit(ctx, S.ContentBlockEndEvent(type="content_block_end", index=block))
        block += 1

    for i, tc in enumerate(tool_calls):
        events += _emit(ctx, S.ToolCallStartEvent(
            type="tool_call_start", tool_call_id=tc["call_id"], tool_name=tc["name"],
            tool_type="function", tool_call_index=i))
        events += _emit(ctx, S.ToolCallDeltaEvent(
            type="tool_call_delta", tool_call_id=tc["call_id"],
            arguments_delta=tc["arguments"], tool_call_index=i))
        events += _emit(ctx, S.ContentBlockEndEvent(type="content_block_end", index=block))
        block += 1

    finish_reason = "tool_calls" if tool_calls and not text else "stop"
    events += _emit(ctx, S.FinishEvent(
        type="finish", finish_reason=S.FinishReason(reason=finish_reason)))
    events += _emit(ctx, S.UsageEvent(type="usage", usage=S.UsageInfo(
        prompt_tokens=usage.get("input_tokens", 0),
        completion_tokens=usage.get("output_tokens", 0),
        total_tokens=usage.get("total_tokens",
                               usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
    )))
    events += _emit(ctx, S.StreamEndEvent(type="stream_end"))

    # Safety net: guarantee the stream terminates with response.completed carrying usage. The
    # converter's StreamEndEvent already produces this, but if a future version stops doing so we
    # synthesize it from the ALCF response rather than emit an incomplete stream.
    if not events or events[-1].get("type") != "response.completed":
        events.append({
            "type": "response.completed",
            "response": {
                "id": resp.get("id", ""),
                "object": "response",
                "model": resp.get("model", ""),
                "status": resp.get("status", "completed"),
                "output": resp.get("output", []),
                "usage": {
                    "input_tokens": usage.get("input_tokens", 0),
                    "output_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get(
                        "total_tokens",
                        usage.get("input_tokens", 0) + usage.get("output_tokens", 0)),
                },
            },
        })
    return events


def sse_wire_format(events: list[dict]) -> bytes:
    """Serialize SSE payload dicts to ``data: {json}\\n\\n`` frames, ending with ``data: [DONE]``."""
    lines = []
    for e in events:
        lines.append(f"data: {json.dumps(e)}\n\n")
    lines.append("data: [DONE]\n\n")
    return "".join(lines).encode()
