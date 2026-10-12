from alcf_proxy import sse


def test_frame():
    out = sse.sse_frame({"type": "x", "n": 1})
    assert out == b'data: {"type": "x", "n": 1}\n\n'


def test_frame_anthropic():
    out = sse.sse_frame({"type": "message_start", "message": {}}, frontend="anthropic")
    assert out.startswith(b"event: message_start\ndata: ")
    assert out.endswith(b"\n\n")


def test_frame_responses():
    out = sse.sse_frame({"type": "response.output_text.delta", "delta": "hi"}, frontend="responses")
    assert out.startswith(b"event: response.output_text.delta\ndata: ")
    assert out.endswith(b"\n\n")


def test_done():
    assert sse.sse_done() == b"data: [DONE]\n\n"
    assert sse.sse_done("responses") == b"data: [DONE]\n\n"
    assert sse.sse_done("anthropic") == b""


def test_parse_data_line():
    assert sse.parse_sse_line('data: {"a": 1}') == {"a": 1}


def test_parse_done_returns_none():
    assert sse.parse_sse_line("data: [DONE]") is None


def test_parse_blank_returns_none():
    assert sse.parse_sse_line("") is None
    assert sse.parse_sse_line("event: ping") is None
