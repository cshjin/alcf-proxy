"""Server-Sent Events codec for the proxy."""
from __future__ import annotations

import json


def sse_frame(payload: dict, frontend: str = "chat") -> bytes:
    if frontend == "anthropic":
        ev_type = payload.get("type", "message_delta")
        return f"event: {ev_type}\ndata: {json.dumps(payload)}\n\n".encode()
    if frontend == "responses":
        ev_type = payload.get("type")
        if ev_type:
            return f"event: {ev_type}\ndata: {json.dumps(payload)}\n\n".encode()
    return f"data: {json.dumps(payload)}\n\n".encode()


def sse_done(frontend: str = "chat") -> bytes:
    if frontend == "anthropic":
        return b""
    return b"data: [DONE]\n\n"


def parse_sse_line(line: str) -> dict | None:
    line = line.strip()
    if not line.startswith("data:"):
        return None
    body = line[len("data:"):].strip()
    if not body or body == "[DONE]":
        return None
    return json.loads(body)
