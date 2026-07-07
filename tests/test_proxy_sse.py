import json
from alcf_run.proxy import sse


def _types(events):
    return [e.get("type") for e in events]


def test_completed_text_produces_ordered_events(fixtures_dir):
    resp = json.loads((fixtures_dir / "alcf_responses_completed.json").read_text())
    events = sse.response_json_to_sse_events(resp)
    t = _types(events)
    assert t[0] == "response.created"
    assert "response.output_text.delta" in t
    assert t[-1] == "response.completed"
    # the delta must carry the assistant text
    deltas = [e for e in events if e.get("type") == "response.output_text.delta"]
    assert any("hello world" in (e.get("delta") or "") for e in deltas)


def test_completed_carries_usage(fixtures_dir):
    resp = json.loads((fixtures_dir / "alcf_responses_completed.json").read_text())
    events = sse.response_json_to_sse_events(resp)
    completed = [e for e in events if e.get("type") == "response.completed"][0]
    assert completed["response"]["usage"]["output_tokens"] >= 1


def test_toolcall_produces_function_call_item(fixtures_dir):
    resp = json.loads((fixtures_dir / "alcf_responses_toolcall.json").read_text())
    events = sse.response_json_to_sse_events(resp)
    # somewhere an output item of type function_call with name get_weather must appear
    blob = json.dumps(events)
    assert "function_call" in blob
    assert "get_weather" in blob
    assert _types(events)[-1] == "response.completed"


def test_wire_format_frames_and_done():
    events = [{"type": "response.completed", "response": {}}]
    wire = sse.sse_wire_format(events)
    assert isinstance(wire, bytes)
    text = wire.decode()
    assert text.startswith("data: ")
    assert text.rstrip().endswith("[DONE]")
    assert "\n\n" in text
