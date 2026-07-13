import httpx
import pytest
from alcf_proxy import upstream


class FakeStream:
    def __init__(self, lines, status=200):
        self._lines = lines
        self.status_code = status
    def __enter__(self): return self
    def __exit__(self, *a): return False
    def iter_lines(self): return iter(self._lines)
    def read(self): return b""
    @property
    def text(self): return ""


def test_stream_chat_yields_chunks(monkeypatch):
    lines = ['data: {"choices":[{"delta":{"content":"hi"}}]}', "data: [DONE]"]
    def fake_stream(method, url, **kw):
        assert kw["headers"]["Authorization"] == "Bearer T"
        assert kw["json"]["stream"] is True
        return FakeStream(lines)
    monkeypatch.setattr(httpx, "stream", fake_stream)
    got = list(upstream.stream_chat({"messages": [], "stream": True}, "T", "sophia", "vllm"))
    assert got == [{"choices": [{"delta": {"content": "hi"}}]}]


def test_maintenance_raises(monkeypatch):
    import json
    def fake_stream(method, url, **kw):
        fs = FakeStream([], status=503)
        fs.read = lambda: json.dumps({"error": {"code": "cluster_under_maintenance"}}).encode()
        return fs
    monkeypatch.setattr(httpx, "stream", fake_stream)
    with pytest.raises(upstream.UpstreamError) as e:
        list(upstream.stream_chat({"messages": []}, "T", "sophia", "vllm"))
    assert "maintenance" in str(e.value).lower()
