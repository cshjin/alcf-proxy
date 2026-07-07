"""FastAPI proxy: stream:true responses -> ALCF stream:false -> re-wrapped SSE."""
from __future__ import annotations

import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .. import auth, endpoints
from . import sse

# ALCF's vLLM backend only accepts tools of type "function". Codex also sends
# provider-hosted tools it expects the OpenAI backend to run: type "namespace"
# (e.g. multi_agent_v1) and "web_search". Forwarding those makes vLLM reject the
# whole request with 400 "tool type <x> not supported", surfaced to codex as a
# generic error. We strip anything that isn't a plain function tool.
_SUPPORTED_TOOL_TYPES = {"function"}


def sanitize_request_body(body: dict) -> dict:
    """Return a copy of the request body safe for ALCF's vLLM responses endpoint.

    - forces stream=False (ALCF rejects streaming)
    - keeps only tools of a vLLM-supported type; if none remain, drops the tools
      key and tool_choice entirely (an empty tools list with tool_choice errors)
    """
    out = dict(body)
    out["stream"] = False
    tools = out.get("tools")
    if isinstance(tools, list):
        kept = [t for t in tools if isinstance(t, dict) and t.get("type") in _SUPPORTED_TOOL_TYPES]
        if kept:
            out["tools"] = kept
        else:
            out.pop("tools", None)
            out.pop("tool_choice", None)
    return out


def build_app(cluster: str, framework: str) -> FastAPI:
    app = FastAPI()
    url = endpoints.responses_url(cluster, framework)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/responses")
    async def responses(request: Request):
        body = sanitize_request_body(await request.json())
        token = auth.get_token()
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        last = None
        for attempt in range(3):
            r = httpx.post(url, json=body, headers=headers, timeout=300)
            if r.status_code == 503:  # cold start
                last = r
                time.sleep(5 * (attempt + 1))
                continue
            if r.status_code != 200:
                return JSONResponse(status_code=r.status_code, content=_safe_json(r))
            events = sse.response_json_to_sse_events(r.json())
            return Response(content=sse.sse_wire_format(events), media_type="text/event-stream")
        return JSONResponse(status_code=503, content=_safe_json(last) if last else {"error": "no response"})

    return app


def _safe_json(r):
    try:
        return r.json()
    except Exception:
        return {"error": r.text[:500]}
