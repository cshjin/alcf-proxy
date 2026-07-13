from alcf_proxy import sse


def test_frame():
    out = sse.sse_frame({"type": "x", "n": 1})
    assert out == b'data: {"type": "x", "n": 1}\n\n'


def test_done():
    assert sse.sse_done() == b"data: [DONE]\n\n"


def test_parse_data_line():
    assert sse.parse_sse_line('data: {"a": 1}') == {"a": 1}


def test_parse_done_returns_none():
    assert sse.parse_sse_line("data: [DONE]") is None


def test_parse_blank_returns_none():
    assert sse.parse_sse_line("") is None
    assert sse.parse_sse_line("event: ping") is None
