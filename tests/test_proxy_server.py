import json
import httpx
import pytest
from fastapi.testclient import TestClient
from alcf_run.proxy import server


@pytest.fixture
def client(monkeypatch, fixtures_dir):
    # stub token
    monkeypatch.setattr("alcf_run.auth.get_token", lambda: "TESTTOK")
    resp_json = json.loads((fixtures_dir / "alcf_responses_completed.json").read_text())

    captured = {}

    def fake_post(url, **kwargs):
        captured["url"] = url
        captured["headers"] = kwargs.get("headers", {})
        captured["json"] = kwargs.get("json", {})
        return httpx.Response(200, json=resp_json)

    monkeypatch.setattr(httpx, "post", fake_post)
    app = server.build_app("sophia", "vllm")
    return TestClient(app), captured


def test_health(client):
    c, _ = client
    assert c.get("/health").json()["status"] == "ok"


def test_responses_forces_nonstream_and_injects_token(client):
    c, captured = client
    r = c.post("/v1/responses", json={"model": "openai/gpt-oss-120b",
                                      "input": "hi", "stream": True})
    assert r.status_code == 200
    # upstream call had stream forced false + bearer injected
    assert captured["json"]["stream"] is False
    assert captured["headers"]["Authorization"] == "Bearer TESTTOK"
    # response body is SSE ending in [DONE]
    body = r.text
    assert "response.completed" in body
    assert body.rstrip().endswith("[DONE]")
