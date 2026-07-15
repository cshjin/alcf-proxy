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


def test_flatten_content_list_to_string_all_roles():
    # ALCF (esp. metis/SambaNova) rejects list-of-parts content on ANY role: it wants a plain
    # string. Every role's structured content must be flattened, not just assistant.
    body = {"messages": [
        {"role": "system", "content": [{"type": "text", "text": "sys"}]},
        {"role": "user", "content": [{"type": "text", "text": "hi"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "hello"}]}]}
    out = sanitizers.sanitize_chat(body)
    for m in out["messages"]:
        assert isinstance(m["content"], str), f"{m['role']} content not flattened"
    by_role = {m["role"]: m["content"] for m in out["messages"]}
    assert by_role == {"system": "sys", "user": "hi", "assistant": "hello"}


def test_flatten_handles_input_and_output_text_parts():
    body = {"messages": [
        {"role": "user", "content": [
            {"type": "input_text", "text": "a"}, {"type": "text", "text": "b"}]},
        {"role": "assistant", "content": [{"type": "output_text", "text": "c"}]}]}
    out = sanitizers.sanitize_chat(body)
    assert out["messages"][0]["content"] == "ab"
    assert out["messages"][1]["content"] == "c"


def test_plain_string_content_untouched():
    body = {"messages": [{"role": "user", "content": "already a string"}]}
    out = sanitizers.sanitize_chat(body)
    assert out["messages"][0]["content"] == "already a string"


def test_forces_stream_true():
    out = sanitizers.sanitize_chat({"messages": [], "stream": False})
    assert out["stream"] is True


def test_does_not_mutate_input():
    import json
    body = {"messages": [], "tools": [{"type": "web_search"}]}
    before = json.dumps(body)
    sanitizers.sanitize_chat(body)
    assert json.dumps(body) == before
