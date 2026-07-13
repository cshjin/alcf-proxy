import json
from alcf_proxy import translate


def _chat_chunks(fixtures_dir):
    from alcf_proxy import sse
    chunks = []
    for line in (fixtures_dir / "alcf_chat_stream.txt").read_text().splitlines():
        d = sse.parse_sse_line(line)
        if d:
            chunks.append(d)
    return chunks


def test_responses_request_to_chat():
    body = {"model": "m", "input": [
        {"type": "message", "role": "user", "content": [{"type": "input_text", "text": "hi"}]}],
        "stream": True}
    chat = translate.to_chat_request("responses", body)
    assert "messages" in chat
    assert chat["messages"][0]["role"] == "user"


def test_chat_request_passthrough_shape():
    body = {"model": "m", "messages": [{"role": "user", "content": "hi"}], "stream": True}
    chat = translate.to_chat_request("chat", body)
    assert chat["messages"][0]["content"] == "hi"


def test_stream_chat_to_responses(fixtures_dir):
    chunks = _chat_chunks(fixtures_dir)
    events = list(translate.stream_to_frontend("responses", iter(chunks)))
    types = [e.get("type") for e in events]
    assert types[0] == "response.created"
    assert "response.output_text.delta" in types
    assert any("hello world" in (e.get("delta") or "") for e in events
               if e.get("type") == "response.output_text.delta")


def test_stream_chat_to_anthropic(fixtures_dir):
    chunks = _chat_chunks(fixtures_dir)
    events = list(translate.stream_to_frontend("anthropic", iter(chunks)))
    types = [e.get("type") for e in events]
    assert types[0] == "message_start"
    assert "content_block_delta" in types
