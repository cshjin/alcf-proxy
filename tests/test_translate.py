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


def test_stream_chat_to_chat_passthrough(fixtures_dir):
    # C1 regression: chat frontend must forward real content (chat chunks have no "type" key).
    chunks = _chat_chunks(fixtures_dir)
    events = list(translate.stream_to_frontend("chat", iter(chunks)))
    assert events, "chat frontend produced no events"
    assert "hello world" in "".join(str(e) for e in events)


def test_responses_stream_has_terminal(fixtures_dir):
    # C2 regression: must end with response.completed even when finish_reason rides the last
    # content chunk (real ALCF shape) and the converter emits no stream_end on its own.
    chunks = _chat_chunks(fixtures_dir)
    types = [e.get("type") for e in translate.stream_to_frontend("responses", iter(chunks))]
    assert types[-1] == "response.completed"


def test_anthropic_stream_has_terminal(fixtures_dir):
    chunks = _chat_chunks(fixtures_dir)
    types = [e.get("type") for e in translate.stream_to_frontend("anthropic", iter(chunks))]
    assert "message_stop" in types
