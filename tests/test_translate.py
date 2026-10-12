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


def test_chunks_to_chat_response(fixtures_dir):
    chunks = _chat_chunks(fixtures_dir)
    resp = translate.chunks_to_chat_response(chunks)
    assert resp["object"] == "chat.completion"
    assert resp["choices"][0]["message"]["content"] == "hello world"
    assert resp["choices"][0]["finish_reason"] == "stop"


def test_response_to_frontend_chat(fixtures_dir):
    chunks = _chat_chunks(fixtures_dir)
    resp = translate.response_to_frontend("chat", chunks)
    assert resp["object"] == "chat.completion"
    assert resp["choices"][0]["message"]["content"] == "hello world"


def test_response_to_frontend_anthropic(fixtures_dir):
    chunks = _chat_chunks(fixtures_dir)
    resp = translate.response_to_frontend("anthropic", chunks)
    assert resp["type"] == "message"
    assert resp["role"] == "assistant"
    assert resp["content"][0]["text"] == "hello world"


def test_response_to_frontend_responses(fixtures_dir):
    chunks = _chat_chunks(fixtures_dir)
    resp = translate.response_to_frontend("responses", chunks)
    assert resp["object"] == "response"
    assert any(item.get("type") == "message" for item in resp["output"])


def test_chunks_to_chat_response_tools_and_reasoning():
    mock_chunks = [
        {"id": "c1", "created": 123456, "model": "test-model", "choices": [{"delta": {"role": "assistant", "reasoning_content": "thinking..."}}]},
        {"id": "c1", "choices": [{"delta": {"tool_calls": [{"index": 0, "id": "call_1", "type": "function", "function": {"name": "run_bash", "arguments": "{\"cmd\": \"ls\"}"}}]}}]},
        {"id": "c1", "choices": [{"finish_reason": "tool_calls", "delta": {}}]},
        {"usage": {"prompt_tokens": 10, "completion_tokens": 20}}
    ]
    resp = translate.chunks_to_chat_response(mock_chunks)
    msg = resp["choices"][0]["message"]
    assert msg["reasoning_content"] == "thinking..."
    assert len(msg["tool_calls"]) == 1
    assert msg["tool_calls"][0]["function"]["name"] == "run_bash"
    assert resp["usage"]["prompt_tokens"] == 10
    assert resp["usage"]["completion_tokens"] == 20

