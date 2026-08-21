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


def test_high_assurance_401_gives_reauth_guidance(monkeypatch):
    # ALCF's 30-day high-assurance policy: token file looks valid but the gateway rejects with
    # 401 "Permission denied from internal policies". Must surface actionable guidance.
    import json
    def fake_stream(method, url, **kw):
        fs = FakeStream([], status=401)
        fs.read = lambda: json.dumps({"error": {"code": "unauthorized", "message":
            "Error: Permission denied from internal policies. This is likely due to a "
            "high-assurance timeout. Please logout ..."}}).encode()
        return fs
    monkeypatch.setattr(httpx, "stream", fake_stream)
    with pytest.raises(upstream.UpstreamError) as e:
        list(upstream.stream_chat({"messages": []}, "T", "sophia", "vllm"))
    msg = str(e.value)
    assert "app.globus.org/logout" in msg
    assert "alcf-proxy auth login" in msg


def test_plain_401_still_reports_status(monkeypatch):
    def fake_stream(method, url, **kw):
        fs = FakeStream([], status=401)
        fs.read = lambda: b'{"error": "bad token"}'
        return fs
    monkeypatch.setattr(httpx, "stream", fake_stream)
    with pytest.raises(upstream.UpstreamError) as e:
        list(upstream.stream_chat({"messages": []}, "T", "sophia", "vllm"))
    assert "401" in str(e.value)


# ---- failover: EndpointSelector ----

ENDPOINTS = [
    {"cluster": "sophia", "framework": "vllm", "model": "openai/gpt-oss-120b"},
    {"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"},
]


def _maint_stream():
    import json
    fs = FakeStream([], status=503)
    fs.read = lambda: json.dumps({"error": {"code": "cluster_under_maintenance"}}).encode()
    return fs


def test_selector_fails_over_to_next_endpoint(monkeypatch):
    calls = []
    def fake_stream(method, url, **kw):
        calls.append(url)
        if "sophia" in url:
            return _maint_stream()  # primary down
        return FakeStream(['data: {"choices":[{"delta":{"content":"hi"}}]}', "data: [DONE]"])
    monkeypatch.setattr(httpx, "stream", fake_stream)
    sel = upstream.EndpointSelector(ENDPOINTS)
    got = list(sel.stream_chat({"model": "REQ", "messages": []}, "T"))
    assert got == [{"choices": [{"delta": {"content": "hi"}}]}]
    # tried sophia first, then metis
    assert "sophia" in calls[0] and "metis" in calls[-1]


def test_selector_remaps_model_per_endpoint(monkeypatch):
    seen = {}
    def fake_stream(method, url, **kw):
        if "sophia" in url:
            return _maint_stream()
        seen["model"] = kw["json"]["model"]
        return FakeStream(["data: [DONE]"])
    monkeypatch.setattr(httpx, "stream", fake_stream)
    sel = upstream.EndpointSelector(ENDPOINTS)
    list(sel.stream_chat({"model": "whatever", "messages": []}, "T"))
    assert seen["model"] == "gpt-oss-120b"  # remapped to metis endpoint's model


def test_selector_sticky_after_failover(monkeypatch):
    calls = []
    def fake_stream(method, url, **kw):
        calls.append(url)
        if "sophia" in url:
            return _maint_stream()
        return FakeStream(["data: [DONE]"])
    monkeypatch.setattr(httpx, "stream", fake_stream)
    sel = upstream.EndpointSelector(ENDPOINTS)
    list(sel.stream_chat({"model": "m", "messages": []}, "T"))
    calls.clear()
    list(sel.stream_chat({"model": "m", "messages": []}, "T"))
    # second request goes straight to metis (sticky), does not re-probe sophia
    assert all("metis" in u for u in calls)


def test_selector_all_down_raises(monkeypatch):
    monkeypatch.setattr(httpx, "stream", lambda method, url, **kw: _maint_stream())
    sel = upstream.EndpointSelector(ENDPOINTS)
    with pytest.raises(upstream.UpstreamError):
        list(sel.stream_chat({"model": "m", "messages": []}, "T"))


def test_selector_active_endpoint(monkeypatch):
    sel = upstream.EndpointSelector(ENDPOINTS)
    assert sel.active() == ENDPOINTS[0]
