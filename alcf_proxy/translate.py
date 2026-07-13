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
