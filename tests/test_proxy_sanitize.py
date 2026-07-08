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


def test_sanitize_flattens_assistant_output_text(fixtures_dir):
    # Multi-turn: codex echoes the prior assistant reply as a message with content =
    # [{"type": "output_text", ...}]. ALCF's vLLM rejects that shape for assistant
    # messages ("Input should be a valid string"). The proxy must flatten assistant
    # content to a plain string.
    body = json.loads((fixtures_dir / "codex_request_multiturn.json").read_text())
    out = server.sanitize_request_body(body)
    assistant = [it for it in out["input"] if it.get("role") == "assistant"]
    assert assistant, "fixture must contain an assistant message"
    for it in assistant:
        assert isinstance(it["content"], str)
        assert it["content"] == "hello"


def test_sanitize_leaves_user_and_developer_content_untouched(fixtures_dir):
    body = json.loads((fixtures_dir / "codex_request_multiturn.json").read_text())
    out = server.sanitize_request_body(body)
    for it in out["input"]:
        if it.get("role") in ("user", "developer"):
            # non-assistant content stays as the original list of parts
            assert isinstance(it["content"], list)


def test_sanitize_handles_string_input():
    # input may be a plain string (not a list of items); must not crash.
    out = server.sanitize_request_body({"model": "m", "input": "hi", "stream": True})
    assert out["input"] == "hi"
