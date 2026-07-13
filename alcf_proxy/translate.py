"""llm-rosetta IR engine: frontend format <-> IR <-> ALCF chat/completions."""
from __future__ import annotations

from typing import Iterator

from llm_rosetta import (
    AnthropicConverter,
    OpenAIChatConverter,
    OpenAIResponsesConverter,
)

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
    target = _converter(frontend)
    src_ctx = _chat.create_stream_context()
    dst_ctx = target.create_stream_context()
    for chunk in chat_chunks:
        for ev in _chat.stream_response_from_provider(chunk, src_ctx):
            for payload in _emit(target, ev, dst_ctx):
                yield payload
