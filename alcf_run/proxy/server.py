"""FastAPI proxy: stream:true responses -> ALCF stream:false -> re-wrapped SSE."""
from __future__ import annotations

import time

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from .. import auth, endpoints
from . import sse


def build_app(cluster: str, framework: str) -> FastAPI:
    app = FastAPI()
    url = endpoints.responses_url(cluster, framework)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    @app.post("/v1/responses")
    async def responses(request: Request):
        body = await request.json()
        body["stream"] = False
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
