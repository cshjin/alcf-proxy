"""Server-Sent Events codec for the proxy."""
from __future__ import annotations

import json


def sse_frame(payload: dict) -> bytes:
    return f"data: {json.dumps(payload)}\n\n".encode()


def sse_done() -> bytes:
    return b"data: [DONE]\n\n"


def parse_sse_line(line: str) -> dict | None:
    line = line.strip()
    if not line.startswith("data:"):
        return None
    body = line[len("data:"):].strip()
    if not body or body == "[DONE]":
        return None
    return json.loads(body)
