"""FastAPI app: translating routes for chat/responses/messages + models + health."""
from __future__ import annotations

import itertools
import os
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.concurrency import run_in_threadpool

from . import endpoints
from . import router as router_mod
from . import sse, translate, upstream
from .formats import FORMATS

_SENTINEL = object()


def build_app(cfg, token_manager) -> FastAPI:
    app = FastAPI()
    # Legacy/fallback chain from config (primary + built-in failover). Sticky across requests.
    fallback_selector = upstream.EndpointSelector(cfg.endpoints())
    # Unified model router: resolves the requested model to whichever cluster(s) serve it, so
    # clients never need per-cluster configuration. An explicit `endpoints:` config bypasses it.
    model_router = router_mod.ModelRouter(cluster_priority=cfg.cluster_priority)
    use_router = not cfg.has_explicit_endpoints()

    # Inbound auth: when ALCF_PROXY_API_KEY is set, every request (except /health) must present it.
    # This is what makes non-loopback binds safe — the proxy injects the user's real ALCF token
    # upstream, so without this check an exposed bind would let anyone spend that token.
    proxy_key = os.environ.get("ALCF_PROXY_API_KEY")
    if proxy_key:
        @app.middleware("http")
        async def _require_proxy_key(request: Request, call_next):
            if request.url.path != "/health":
                got = request.headers.get("authorization", "")
                if not secrets.compare_digest(got, f"Bearer {proxy_key}"):
                    return JSONResponse(
                        status_code=401,
                        content={"error": "invalid or missing proxy API key "
                                          "(Authorization: Bearer <ALCF_PROXY_API_KEY>)"})
            return await call_next(request)

    def _selector_for(chat_body: dict, token: str) -> upstream.EndpointSelector:
        """Unified routing by requested model; fall back to the configured chain when the
        catalog is unavailable (e.g. list-endpoints outage) or no model was given."""
        model = chat_body.get("model")
        if not (use_router and model):
            return fallback_selector
        try:
            return model_router.selector_for(model, token)
        except (router_mod.UnknownModelError, endpoints.GatewayAuthError):
            raise
        except Exception:  # noqa: BLE001 - catalog fetch failure: keep serving via the chain
            return fallback_selector

    def _make_route(path: str, spec):
        async def route(request: Request):
            try:
                body = await request.json()
            except Exception:  # noqa: BLE001
                return JSONResponse(status_code=400, content={"error": "invalid JSON body"})
            chat_body = spec.sanitize(translate.to_chat_request(spec.name, body))

            # Token fetch, routing (may hit the catalog), and the first-chunk probe are all
            # blocking I/O — run them in a worker thread so the event loop (and /health) stays
            # responsive. The probe also ensures upstream failures surface as a clean 502/400
            # instead of a broken 200 after headers are committed.
            def _resolve_and_probe():
                token = token_manager.get_valid_token()
                selector = _selector_for(chat_body, token)
                chunks = selector.stream_chat(chat_body, token)
                return chunks, next(chunks, _SENTINEL)

            try:
                chunks, first = await run_in_threadpool(_resolve_and_probe)
            except router_mod.UnknownModelError as e:
                return JSONResponse(status_code=400, content={"error": str(e)})
            except endpoints.GatewayAuthError as e:
                return JSONResponse(status_code=502, content={"error": str(e)})
            except upstream.UpstreamError as e:
                return JSONResponse(status_code=502, content={"error": str(e)})

            def gen():
                buffered = () if first is _SENTINEL else (first,)
                for payload in translate.stream_to_frontend(
                        spec.name, itertools.chain(buffered, chunks)):
                    yield sse.sse_frame(payload)
                yield sse.sse_done()
            return StreamingResponse(gen(), media_type="text/event-stream")
        return route

    for path, spec in FORMATS.items():
        app.add_api_route(path, _make_route(path, spec), methods=["POST"])

    @app.get("/v1/models")
    async def models():
        try:
            if use_router:
                def _pool():
                    return model_router.models(token_manager.get_valid_token())
                data = await run_in_threadpool(_pool)
            else:
                # Explicit endpoints pin the chain regardless of the requested model — advertise
                # exactly what the chain serves, not the whole catalog.
                data, seen = [], set()
                for e in cfg.endpoints():
                    if e["model"] not in seen:
                        seen.add(e["model"])
                        data.append({"id": e["model"], "object": "model",
                                     "owned_by": f"{e['cluster']}/{e['framework']}"})
            return {"object": "list", "data": data}
        except Exception as e:  # noqa: BLE001
            return JSONResponse(status_code=502, content={"error": str(e)})

    @app.get("/health")
    def health():
        hrs = token_manager.hours_left()
        status = "ok"
        if hrs is not None and hrs < 0.1:
            status = "degraded"
        active = fallback_selector.active()
        return {
            "status": status,
            "upstream": "unknown",
            "token_hours_left": hrs,
            "routing": "explicit" if cfg.has_explicit_endpoints() else "unified",
            "cluster": active["cluster"],
            "framework": active["framework"],
            "active_endpoint": active,
            "endpoints": cfg.endpoints(),
        }

    return app
