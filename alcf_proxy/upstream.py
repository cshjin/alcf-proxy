"""ALCF chat/completions streaming client with Bearer injection + 503 handling."""
from __future__ import annotations

import time
from typing import Iterator

import httpx

from . import endpoints, sse


class UpstreamError(Exception):
    pass


def stream_chat(chat_body: dict, token: str, cluster: str, framework: str,
                max_cold_retries: int = 3) -> Iterator[dict]:
    body = dict(chat_body)
    body["stream"] = True
    url = endpoints.chat_url(cluster, framework)
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    attempt = 0
    while True:
        with httpx.stream("POST", url, json=body, headers=headers, timeout=300) as r:
            if r.status_code == 503:
                raw = r.read().decode(errors="replace")
                if "maintenance" in raw.lower():
                    raise UpstreamError(f"ALCF cluster under maintenance: {raw[:200]}")
                if attempt < max_cold_retries:
                    attempt += 1
                    time.sleep(5 * attempt)
                    continue
                raise UpstreamError(f"ALCF cold-start did not become ready: {raw[:200]}")
            if r.status_code != 200:
                raw = r.read().decode(errors="replace")
                raise UpstreamError(f"ALCF HTTP {r.status_code}: {raw[:300]}")
            for line in r.iter_lines():
                d = sse.parse_sse_line(line if isinstance(line, str) else line.decode())
                if d is not None:
                    yield d
            return
