import pytest
from fastapi.testclient import TestClient
from alcf_proxy import server, config


class FakeTM:
    def get_valid_token(self): return "TESTTOK"
    def hours_left(self): return 40.0


@pytest.fixture
def client(monkeypatch, fixtures_dir):
    cfg = config.Config({"cluster": "sophia", "framework": "vllm"})
    chunks = []
    from alcf_proxy import sse as _sse
    for line in (fixtures_dir / "alcf_chat_stream.txt").read_text().splitlines():
        d = _sse.parse_sse_line(line)
        if d:
            chunks.append(d)
    captured = {}

    # patch EndpointSelector.stream_chat (the server drives failover through the selector)
    def fake_sel_stream(self, body, token):
        captured["body"] = body
        captured["token"] = token
        return iter(chunks)
    monkeypatch.setattr("alcf_proxy.server.upstream.EndpointSelector.stream_chat", fake_sel_stream)
    app = server.build_app(cfg, FakeTM())
    return TestClient(app), captured


def test_health(client):
    c, _ = client
    j = c.get("/health").json()
    assert j["status"] in ("ok", "degraded")
    assert j["cluster"] == "sophia"
    assert j["token_hours_left"] == 40.0


def test_health_reports_endpoints(client):
    c, _ = client
    j = c.get("/health").json()
    assert "active_endpoint" in j
    assert j["active_endpoint"]["cluster"] == "sophia"
    assert isinstance(j["endpoints"], list) and len(j["endpoints"]) >= 1


def test_responses_route_streams_and_injects_token(client):
    c, captured = client
    r = c.post("/v1/responses", json={"model": "openai/gpt-oss-120b",
                                      "input": [{"type": "message", "role": "user",
                                                 "content": [{"type": "input_text", "text": "hi"}]}],
                                      "stream": True})
    assert r.status_code == 200
    assert captured["token"] == "TESTTOK"
    assert captured["body"]["stream"] is True
    body = r.text
    assert "response.output_text.delta" in body
    assert body.rstrip().endswith("[DONE]")


def test_messages_route(client):
    c, _ = client
    r = c.post("/v1/messages", json={"model": "openai/gpt-oss-120b",
                                     "messages": [{"role": "user", "content": "hi"}],
                                     "stream": True})
    assert r.status_code == 200
    assert "message_start" in r.text


def test_models_route(client, monkeypatch):
    c, _ = client
    monkeypatch.setattr("alcf_proxy.server.endpoints.list_models",
                        lambda tok: ["sophia/vllm: openai/gpt-oss-120b"])
    r = c.get("/v1/models")
    assert r.status_code == 200
    assert "gpt-oss-120b" in r.text
