import json

from alcf_run.proxy import server


def test_sanitize_keeps_only_function_tools(fixtures_dir):
    body = json.loads((fixtures_dir / "codex_request_tools.json").read_text())
    out = server.sanitize_request_body(body)
    kinds = [t.get("type") for t in out["tools"]]
    assert kinds == ["function", "function", "function"]
    # non-function tools (namespace, web_search) are dropped
    assert all(t.get("type") == "function" for t in out["tools"])


def test_sanitize_forces_stream_false(fixtures_dir):
    body = json.loads((fixtures_dir / "codex_request_tools.json").read_text())
    out = server.sanitize_request_body(body)
    assert out["stream"] is False


def test_sanitize_does_not_mutate_input(fixtures_dir):
    body = json.loads((fixtures_dir / "codex_request_tools.json").read_text())
    before = json.dumps(body)
    server.sanitize_request_body(body)
    assert json.dumps(body) == before  # original untouched (pure)


def test_sanitize_handles_no_tools():
    out = server.sanitize_request_body({"model": "m", "input": "hi", "stream": True})
    assert out["stream"] is False
    assert "tools" not in out or out["tools"] == []


def test_sanitize_empty_tools_list_dropped():
    # ALCF rejects an empty tools array with tool_choice; if all tools filtered out,
    # tools should be removed entirely (not left as []).
    out = server.sanitize_request_body(
        {"model": "m", "input": "hi", "stream": True,
         "tools": [{"type": "web_search"}], "tool_choice": "auto"})
    assert not out.get("tools")
    assert "tool_choice" not in out
