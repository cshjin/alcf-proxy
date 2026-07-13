"""Live end-to-end tests against the real ALCF gateway.

Marked @pytest.mark.live and skipped by default (the pyproject addopts excludes 'live').
Run explicitly with:  python -m pytest -m live -o addopts="" -q

Requires a prior login (alcf-proxy auth login) and at least one
up cluster. Uses the default failover chain, so it works even if sophia is under maintenance
(it will fall back to metis automatically).
"""
import pytest
from fastapi.testclient import TestClient

from alcf_proxy import auth, config, server


@pytest.mark.live
def test_responses_stream_end_to_end():
    cfg = config.load_config()
    app = server.build_app(cfg, auth.TokenManager())
    client = TestClient(app)
    r = client.post(
        "/v1/responses",
        json={
            "model": "gpt-oss-120b",
            "input": [{"type": "message", "role": "user",
                       "content": [{"type": "input_text", "text": "say exactly: hello world"}]}],
            "stream": True,
            "max_output_tokens": 64,
        },
    )
    assert r.status_code == 200
    body = r.text
    assert "response.output_text.delta" in body
    assert "response.completed" in body  # terminal frame must be present (C2 regression)
    assert body.rstrip().endswith("[DONE]")


@pytest.mark.live
def test_messages_stream_end_to_end():
    cfg = config.load_config()
    app = server.build_app(cfg, auth.TokenManager())
    client = TestClient(app)
    r = client.post(
        "/v1/messages",
        json={
            "model": "gpt-oss-120b",
            "messages": [{"role": "user", "content": "say hi"}],
            "stream": True,
            "max_tokens": 64,
        },
    )
    assert r.status_code == 200
    assert "message_start" in r.text
    assert "message_stop" in r.text  # terminal frame must be present (C2 regression)


@pytest.mark.live
def test_models_live():
    tm = auth.TokenManager()
    from alcf_proxy import endpoints
    models = endpoints.list_models(tm.get_valid_token())
    assert any("gpt-oss-120b" in m for m in models)
