import pytest
from fastapi.testclient import TestClient
from alcf_proxy import server, config


class FakeTM:
    def get_valid_token(self): return "TESTTOK"
    def hours_left(self): return 40.0


CATALOG = {
    "clusters": {
        "sophia": {"frameworks": {"vllm": {"models": ["openai/gpt-oss-120b"]}}},
        "metis": {"frameworks": {"api": {"models": ["gpt-oss-120b"]}}},
        "minerva": {"frameworks": {"api": {"models": ["nemotron-3-ultra"]}}},
    }
}


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

    # offline catalog for the model router
    monkeypatch.setattr("alcf_proxy.endpoints.fetch_list_endpoints", lambda tok: CATALOG)

    # patch EndpointSelector.stream_chat (the server drives failover through selectors)
    def fake_sel_stream(self, body, token):
        captured["body"] = body
        captured["token"] = token
        captured["endpoints"] = [dict(e) for e in self._endpoints]
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
    assert j["routing"] == "unified"


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


def test_unified_routing_resolves_basename_across_clusters(client):
    # Client asks for the metis-style id; router must route it (sophia first by priority),
    # with per-endpoint local model ids in the failover chain.
    c, captured = client
    r = c.post("/v1/messages", json={"model": "gpt-oss-120b",
                                     "messages": [{"role": "user", "content": "hi"}],
                                     "stream": True})
    assert r.status_code == 200
    eps = captured["endpoints"]
    assert [e["cluster"] for e in eps] == ["sophia", "metis"]
    assert eps[0]["model"] == "openai/gpt-oss-120b"


def test_unknown_model_returns_400(client):
    c, _ = client
    r = c.post("/v1/messages", json={"model": "no-such-model",
                                     "messages": [{"role": "user", "content": "hi"}],
                                     "stream": True})
    assert r.status_code == 400
    assert "alcf-proxy models" in r.text


def test_messages_route(client):
    c, _ = client
    r = c.post("/v1/messages", json={"model": "openai/gpt-oss-120b",
                                     "messages": [{"role": "user", "content": "hi"}],
                                     "stream": True})
    assert r.status_code == 200
    assert "message_start" in r.text


def test_models_route_openai_shape(client):
    c, _ = client
    r = c.get("/v1/models")
    assert r.status_code == 200
    j = r.json()
    assert j["object"] == "list"
    ids = [m["id"] for m in j["data"]]
    assert "openai/gpt-oss-120b" in ids and "nemotron-3-ultra" in ids
    assert all(m.get("owned_by") for m in j["data"])


def test_catalog_outage_falls_back_to_configured_chain(monkeypatch, fixtures_dir):
    # If list-endpoints is unavailable, routing falls back to the configured chain instead of
    # failing every request.
    cfg = config.Config({"cluster": "sophia", "framework": "vllm"})
    monkeypatch.setattr("alcf_proxy.endpoints.fetch_list_endpoints",
                        lambda tok: (_ for _ in ()).throw(RuntimeError("catalog down")))
    chunks = []
    from alcf_proxy import sse as _sse
    for line in (fixtures_dir / "alcf_chat_stream.txt").read_text().splitlines():
        d = _sse.parse_sse_line(line)
        if d:
            chunks.append(d)
    seen = {}

    def fake_sel_stream(self, body, token):
        seen["endpoints"] = [dict(e) for e in self._endpoints]
        return iter(chunks)
    monkeypatch.setattr("alcf_proxy.server.upstream.EndpointSelector.stream_chat", fake_sel_stream)
    app = server.build_app(cfg, FakeTM())
    c = TestClient(app)
    r = c.post("/v1/messages", json={"model": "openai/gpt-oss-120b",
                                     "messages": [{"role": "user", "content": "hi"}],
                                     "stream": True})
    assert r.status_code == 200
    # fell back to the config-synthesized chain (sophia primary + built-in failover)
    assert seen["endpoints"][0]["cluster"] == "sophia"
    assert len(seen["endpoints"]) >= 2


def test_explicit_endpoints_config_bypasses_router(monkeypatch, fixtures_dir):
    cfg = config.Config({"endpoints": [
        {"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"}]})
    monkeypatch.setattr("alcf_proxy.endpoints.fetch_list_endpoints", lambda tok: CATALOG)
    chunks = []
    from alcf_proxy import sse as _sse
    for line in (fixtures_dir / "alcf_chat_stream.txt").read_text().splitlines():
        d = _sse.parse_sse_line(line)
        if d:
            chunks.append(d)
    seen = {}

    def fake_sel_stream(self, body, token):
        seen["endpoints"] = [dict(e) for e in self._endpoints]
        return iter(chunks)
    monkeypatch.setattr("alcf_proxy.server.upstream.EndpointSelector.stream_chat", fake_sel_stream)
    app = server.build_app(cfg, FakeTM())
    c = TestClient(app)
    r = c.post("/v1/messages", json={"model": "anything",
                                     "messages": [{"role": "user", "content": "hi"}],
                                     "stream": True})
    assert r.status_code == 200
    assert seen["endpoints"] == [{"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"}]
    assert c.get("/health").json()["routing"] == "explicit"


def test_explicit_mode_models_lists_chain_not_catalog(monkeypatch):
    # With an explicit endpoints: override, /v1/models must advertise what the chain actually
    # serves — not the full catalog (which would let a GUI pick a model it can never get).
    cfg = config.Config({"endpoints": [
        {"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"}]})
    monkeypatch.setattr("alcf_proxy.endpoints.fetch_list_endpoints", lambda tok: CATALOG)
    app = server.build_app(cfg, FakeTM())
    c = TestClient(app)
    j = c.get("/v1/models").json()
    assert [m["id"] for m in j["data"]] == ["gpt-oss-120b"]


def test_proxy_api_key_enforced_when_set(monkeypatch, fixtures_dir):
    # ALCF_PROXY_API_KEY must be ENFORCED inbound (not just permission-to-bind): the proxy
    # injects the user's real ALCF token upstream.
    monkeypatch.setenv("ALCF_PROXY_API_KEY", "sekret")
    monkeypatch.setattr("alcf_proxy.endpoints.fetch_list_endpoints", lambda tok: CATALOG)
    cfg = config.Config({})
    app = server.build_app(cfg, FakeTM())
    c = TestClient(app)
    # /health stays open (liveness)
    assert c.get("/health").status_code == 200
    # wrong/missing key -> 401
    assert c.get("/v1/models").status_code == 401
    assert c.get("/v1/models", headers={"Authorization": "Bearer wrong"}).status_code == 401
    r = c.post("/v1/messages", headers={"Authorization": "Bearer wrong"},
               json={"model": "gpt-oss-120b", "messages": [], "stream": True})
    assert r.status_code == 401
    # correct key -> passes auth
    assert c.get("/v1/models",
                 headers={"Authorization": "Bearer sekret"}).status_code == 200


def test_no_proxy_api_key_means_open_localhost(monkeypatch):
    monkeypatch.delenv("ALCF_PROXY_API_KEY", raising=False)
    monkeypatch.setattr("alcf_proxy.endpoints.fetch_list_endpoints", lambda tok: CATALOG)
    app = server.build_app(config.Config({}), FakeTM())
    c = TestClient(app)
    assert c.get("/v1/models").status_code == 200


def test_all_endpoints_down_returns_502_not_broken_200(monkeypatch, fixtures_dir):
    # C3 regression: if upstream is unavailable, the client must get a clean 502, not a 200 with
    # an empty/silent body (which happens if the failure is raised inside the stream generator).
    cfg = config.Config({"cluster": "sophia", "framework": "vllm"})
    monkeypatch.setattr("alcf_proxy.endpoints.fetch_list_endpoints", lambda tok: CATALOG)

    def boom(self, body, token):
        raise __import__("alcf_proxy.upstream", fromlist=["UpstreamError"]).UpstreamError("all down")
    monkeypatch.setattr("alcf_proxy.server.upstream.EndpointSelector.stream_chat", boom)
    app = server.build_app(cfg, FakeTM())
    c = TestClient(app)
    r = c.post("/v1/responses", json={"model": "openai/gpt-oss-120b",
               "input": [{"type": "message", "role": "user",
                          "content": [{"type": "input_text", "text": "hi"}]}], "stream": True})
    assert r.status_code == 502
    assert "down" in r.text.lower() or "error" in r.text.lower()
