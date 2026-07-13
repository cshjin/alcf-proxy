"""FastAPI app: translating routes for chat/responses/messages + models + health."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse

from . import endpoints, sse, translate, upstream
from .formats import FORMATS


def build_app(cfg, token_manager) -> FastAPI:
    app = FastAPI()
    # One selector shared across requests: it stays sticky on a working endpoint and fails over
    # to the next configured endpoint when a cluster goes down (503/maintenance).
    selector = upstream.EndpointSelector(cfg.endpoints())

    def _make_route(path: str, spec):
        async def route(request: Request):
            body = await request.json()
            chat_body = spec.sanitize(translate.to_chat_request(spec.name, body))
            token = token_manager.get_valid_token()

            def gen():
                chunks = selector.stream_chat(chat_body, token)
                for payload in translate.stream_to_frontend(spec.name, chunks):
                    yield sse.sse_frame(payload)
                yield sse.sse_done()
            return StreamingResponse(gen(), media_type="text/event-stream")
        return route

    for path, spec in FORMATS.items():
        app.add_api_route(path, _make_route(path, spec), methods=["POST"])

    @app.get("/v1/models")
    def models():
        try:
            return {"data": endpoints.list_models(token_manager.get_valid_token())}
        except Exception as e:  # noqa: BLE001
            return JSONResponse(status_code=502, content={"error": str(e)})

    @app.get("/health")
    def health():
        hrs = token_manager.hours_left()
        status = "ok"
        if hrs is not None and hrs < 0.1:
            status = "degraded"
        active = selector.active()
        return {
            "status": status,
            "upstream": "unknown",
            "token_hours_left": hrs,
            "cluster": active["cluster"],
            "framework": active["framework"],
            "active_endpoint": active,
            "endpoints": cfg.endpoints(),
        }

    return app
