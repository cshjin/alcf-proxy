"""llm-rosetta IR engine: frontend format <-> IR <-> ALCF chat/completions."""
from __future__ import annotations

from typing import Iterator

from llm_rosetta import (
    AnthropicConverter,
    OpenAIChatConverter,
    OpenAIResponsesConverter,
)
from llm_rosetta.types.ir import stream as _S

_CONVERTERS = {
    "chat": OpenAIChatConverter,
    "responses": OpenAIResponsesConverter,
    "anthropic": AnthropicConverter,
}
_chat = OpenAIChatConverter()


def _converter(frontend: str):
    return _CONVERTERS[frontend]()


def to_chat_request(frontend: str, body: dict) -> dict:
    conv = _converter(frontend)
    ir = conv.request_from_provider(body)
    result = _chat.request_to_provider(ir)
    return result[0] if isinstance(result, (list, tuple)) else result


def _emit(target, event, ctx) -> list[dict]:
    out = target.stream_response_to_provider(event, ctx)
    if out is None:
        return []
    items = out if isinstance(out, list) else [out]
    return [p for p in items if isinstance(p, dict) and p.get("type")]


def stream_to_frontend(frontend: str, chat_chunks) -> Iterator[dict]:
    # The upstream is already chat/completions, so the chat frontend is an identity passthrough.
    # (Chat chunks have no "type" key, so they must NOT go through the IR converter/_emit filter.)
    if frontend == "chat":
        yield from chat_chunks
        return

    target = _converter(frontend)
    src_ctx = _chat.create_stream_context()
    dst_ctx = target.create_stream_context()
    saw_stream_end = False
    for chunk in chat_chunks:
        for ev in _chat.stream_response_from_provider(chunk, src_ctx):
            if isinstance(ev, dict) and ev.get("type") == "stream_end":
                saw_stream_end = True
            for payload in _emit(target, ev, dst_ctx):
                yield payload
    # ALCF puts finish_reason on the last content chunk, so the chat converter emits a `finish` IR
    # event but no `stream_end`. Target converters need stream_end to flush their terminal frame
    # (response.completed / message_stop). Synthesize it if we didn't see one.
    if not saw_stream_end:
        for payload in _emit(target, _S.StreamEndEvent(type="stream_end"), dst_ctx):
            yield payload


def chunks_to_chat_response(chat_chunks) -> dict:
    import time

    content = ""
    reasoning_content = ""
    tool_calls: list[dict] = []
    finish_reason = "stop"
    model = ""
    resp_id = "chatcmpl-"
    created = 0
    prompt_tokens = 0
    completion_tokens = 0
    for c in chat_chunks:
        if not isinstance(c, dict):
            continue
        resp_id = c.get("id") or resp_id
        model = c.get("model") or model
        if c.get("created"):
            created = c["created"]
        usage = c.get("usage")
        if usage:
            prompt_tokens = usage.get("prompt_tokens", prompt_tokens)
            completion_tokens = usage.get("completion_tokens", completion_tokens)
        for choice in c.get("choices", []):
            if choice.get("finish_reason"):
                finish_reason = choice["finish_reason"]
            delta = choice.get("delta", {})
            if delta.get("content"):
                content += delta["content"]
            if delta.get("reasoning_content"):
                reasoning_content += delta["reasoning_content"]
            if delta.get("tool_calls"):
                for tc in delta["tool_calls"]:
                    idx = tc.get("index", len(tool_calls))
                    while len(tool_calls) <= idx:
                        tool_calls.append({"id": "", "type": "function", "function": {"name": "", "arguments": ""}})
                    if tc.get("id"):
                        tool_calls[idx]["id"] = tc["id"]
                    if tc.get("type"):
                        tool_calls[idx]["type"] = tc["type"]
                    fn = tc.get("function", {})
                    if fn.get("name"):
                        tool_calls[idx]["function"]["name"] += fn["name"]
                    if fn.get("arguments"):
                        tool_calls[idx]["function"]["arguments"] += fn["arguments"]
    msg: dict = {"role": "assistant", "content": content if (content or not tool_calls) else None}
    if tool_calls:
        msg["tool_calls"] = tool_calls
    if reasoning_content:
        msg["reasoning_content"] = reasoning_content
    return {
        "id": resp_id,
        "object": "chat.completion",
        "created": created or int(time.time()),
        "model": model,
        "choices": [{"index": 0, "message": msg, "finish_reason": finish_reason}],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens or len(content.split()),
            "total_tokens": prompt_tokens + (completion_tokens or len(content.split())),
        },
    }


def response_to_frontend(frontend: str, chat_chunks) -> dict:
    accum = chunks_to_chat_response(chat_chunks)
    if frontend == "chat":
        return accum
    target = _converter(frontend)
    ir = _chat.response_from_provider(accum)
    return target.response_to_provider(ir)

