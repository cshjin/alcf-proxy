"""ALCF chat/completions streaming client with Bearer injection + 503 handling + failover."""
from __future__ import annotations

import time
from typing import Iterator

import httpx

from . import endpoints, sse


class UpstreamError(Exception):
    pass


class EndpointDown(UpstreamError):
    """Raised internally when an endpoint is unavailable (maintenance / cold-start exhausted)."""


def stream_chat(chat_body: dict, token: str, cluster: str, framework: str,
                max_cold_retries: int = 3) -> Iterator[dict]:
    """Stream chat chunks from one ALCF endpoint. Raises EndpointDown if the cluster is
    unavailable (503 maintenance, or cold-start that never became ready), UpstreamError on
    other non-200s."""
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
                    raise EndpointDown(f"ALCF cluster under maintenance: {raw[:200]}")
                if attempt < max_cold_retries:
                    attempt += 1
                    time.sleep(5 * attempt)
                    continue
                raise EndpointDown(f"ALCF cold-start did not become ready: {raw[:200]}")
            if r.status_code != 200:
                raw = r.read().decode(errors="replace")
                if endpoints.policy_401(r.status_code, raw):
                    raise UpstreamError(
                        f"{endpoints.REAUTH_GUIDANCE}\n--- gateway said ---\n{raw[:300]}")
                raise UpstreamError(f"ALCF HTTP {r.status_code}: {raw[:300]}")
            for line in r.iter_lines():
                d = sse.parse_sse_line(line if isinstance(line, str) else line.decode())
                if d is not None:
                    yield d
            return


class EndpointSelector:
    """Try a list of endpoints in order, failing over on EndpointDown.

    Sticky: once an endpoint works, subsequent requests start there (so we don't re-probe a
    known-down primary every request). Each endpoint has its own model id, which replaces the
    request's model before forwarding.
    """

    def __init__(self, endpoint_list: list[dict], max_cold_retries: int = 3):
        if not endpoint_list:
            raise ValueError("EndpointSelector requires at least one endpoint")
        self._endpoints = [dict(e) for e in endpoint_list]
        self._idx = 0
        self._max_cold_retries = max_cold_retries

    def active(self) -> dict:
        return self._endpoints[self._idx]

    def stream_chat(self, chat_body: dict, token: str) -> Iterator[dict]:
        errors = []
        n = len(self._endpoints)
        for offset in range(n):
            idx = (self._idx + offset) % n
            ep = self._endpoints[idx]
            body = dict(chat_body)
            body["model"] = ep["model"]
            gen = stream_chat(body, token, ep["cluster"], ep["framework"],
                              max_cold_retries=self._max_cold_retries)
            try:
                first = next(gen)
            except EndpointDown as e:
                errors.append(f"{ep['cluster']}/{ep['framework']}: {e}")
                continue
            except StopIteration:
                # endpoint responded 200 but produced no chunks; treat as success (empty)
                self._idx = idx
                return iter(())
            # endpoint is alive — stick to it and stream everything
            self._idx = idx

            def _chunks(first_chunk=first, generator=gen):
                yield first_chunk
                yield from generator
            return _chunks()
        raise UpstreamError("All ALCF endpoints unavailable:\n" + "\n".join(errors))
