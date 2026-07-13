from alcf_proxy.formats import sanitizers


def test_strip_non_function_tools():
    body = {"messages": [], "tools": [
        {"type": "function", "function": {"name": "f"}},
        {"type": "namespace"}, {"type": "web_search"}]}
    out = sanitizers.sanitize_chat(body)
    assert all(t["type"] == "function" for t in out["tools"])
    assert len(out["tools"]) == 1


def test_empty_tools_dropped_with_tool_choice():
    body = {"messages": [], "tools": [{"type": "web_search"}], "tool_choice": "auto"}
    out = sanitizers.sanitize_chat(body)
    assert not out.get("tools")
    assert "tool_choice" not in out


def test_flatten_assistant_content_list_to_string():
    body = {"messages": [
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "hello"}]}]}
    out = sanitizers.sanitize_chat(body)
    assistant = [m for m in out["messages"] if m["role"] == "assistant"][0]
    assert assistant["content"] == "hello"


def test_forces_stream_true():
    out = sanitizers.sanitize_chat({"messages": [], "stream": False})
    assert out["stream"] is True


def test_does_not_mutate_input():
    import json
    body = {"messages": [], "tools": [{"type": "web_search"}]}
    before = json.dumps(body)
    sanitizers.sanitize_chat(body)
    assert json.dumps(body) == before
