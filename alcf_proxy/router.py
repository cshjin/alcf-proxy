"""Unified model routing: one pool of models across all ALCF clusters.

Clients just name a model; the router resolves which cluster(s) serve it and returns an ordered
endpoint list for failover. Model ids differ per cluster (sophia `openai/gpt-oss-120b` vs metis
`gpt-oss-120b`), so exact ids AND basenames are treated as **aliases of the same logical model**;
candidate ordering is always by `cluster_priority` (priority wins over exact-vs-basename). If two
clusters ever serve *different* models sharing a basename, a warning is logged at table build.

The catalog comes from the gateway's `list-endpoints`, cached with a TTL. The fetch happens
OUTSIDE the lock (never blocks other requests on the network), a failed refresh keeps serving the
stale table, and failures are negative-cached for `retry_backoff_s` so a slow/broken catalog
endpoint cannot stall every request.
"""
from __future__ import annotations

import logging
import re
import threading
import time
from typing import Callable

from . import endpoints
from .upstream import EndpointSelector

log = logging.getLogger("alcf_proxy.router")

COMMON_ALIASES = {
    "inkling": "inkling-bf16",
}


class UnknownModelError(Exception):
    """The requested model is not served by any ALCF cluster (per current catalog)."""


def normalize_model_name(model_id: str) -> str:
    """Strip context-window suffix tags like [1m], [200k], etc."""
    return re.sub(r"\[\d+[kKmM]?\]$", "", model_id.strip())


def _basename(model_id: str) -> str:
    cleaned = normalize_model_name(model_id)
    if cleaned.casefold().startswith("alcf:"):
        cleaned = cleaned[5:]
    base = cleaned.rsplit("/", 1)[-1].casefold()
    return COMMON_ALIASES.get(base, base)


class ModelRouter:
    def __init__(
        self,
        cluster_priority: tuple[str, ...] | list[str] = ("sophia", "metis", "minerva"),
        ttl_s: float = 600,
        retry_backoff_s: float = 30,
        fetch: Callable[[str], dict] | None = None,
        unknown_model_fallback: str | None = None,
    ):
        self._priority = list(cluster_priority)
        self._ttl = ttl_s
        self._backoff = retry_backoff_s
        self._fetch = fetch or endpoints.fetch_list_endpoints
        self._unknown_fallback = unknown_model_fallback
        self._lock = threading.Lock()
        self._table: list[dict] | None = None  # [{cluster, framework, model}]
        self._fetched_at: float = 0.0
        self._last_attempt: float = 0.0
        self._selectors: dict[str, tuple[tuple, EndpointSelector]] = {}

    # -- catalog ---------------------------------------------------------

    def _prio(self, cluster: str) -> int:
        try:
            return self._priority.index(cluster)
        except ValueError:
            return len(self._priority)  # unknown clusters go last, stable order

    def _build_table(self, payload: dict) -> list[dict]:
        table = []
        for cluster, cval in (payload.get("clusters") or {}).items():
            for fw, fval in (cval.get("frameworks") or {}).items():
                for m in fval.get("models") or []:
                    mid = m if isinstance(m, str) else (m.get("id") or m.get("name"))
                    if mid:
                        table.append({"cluster": cluster, "framework": fw, "model": mid})
        table.sort(key=lambda e: self._prio(e["cluster"]))
        # Detect basename collisions: distinct full ids sharing a basename would silently
        # failover between different models — surface it loudly.
        by_base: dict[str, set] = {}
        for e in table:
            by_base.setdefault(_basename(e["model"]), set()).add(e["model"])
        for base, ids in by_base.items():
            if len(ids) > 1 and base not in {i.casefold() for i in ids}:
                log.warning("basename %r groups distinct model ids %s — "
                            "cross-cluster failover would switch models", base, sorted(ids))
        return table

    def _ensure_table(self, token: str) -> list[dict]:
        now = time.monotonic()
        with self._lock:
            table = self._table
            fresh = table is not None and (now - self._fetched_at) < self._ttl
            backing_off = (now - self._last_attempt) < self._backoff
            if fresh or (table is not None and backing_off):
                return list(table)
            self._last_attempt = now  # claim the refresh slot (negative-cache on failure)
        # Fetch OUTSIDE the lock: a slow catalog endpoint must never block other requests.
        try:
            payload = self._fetch(token)
        except endpoints.GatewayAuthError:
            raise  # auth is fatal for everything; surface the re-auth guidance immediately
        except Exception as e:  # noqa: BLE001
            with self._lock:
                if self._table is None:
                    raise  # no stale table to fall back to
                log.warning("catalog refresh failed (%s); serving stale table for %ss",
                            e, self._backoff)
                return list(self._table)
        new_table = self._build_table(payload)
        with self._lock:
            self._table = new_table
            self._fetched_at = time.monotonic()
            return list(new_table)

    # -- routing ---------------------------------------------------------

    def routes_for(self, model: str, token: str) -> list[dict]:
        """Ordered [{cluster, framework, model}] serving `model` (exact id or basename alias)."""
        table = self._ensure_table(token)
        cleaned_model = normalize_model_name(model)
        want, want_base = cleaned_model.casefold(), _basename(cleaned_model)
        exact = [e for e in table if e["model"].casefold() == want]
        seen = {(e["cluster"], e["framework"]) for e in exact}
        base = [e for e in table
                if _basename(e["model"]) == want_base
                and (e["cluster"], e["framework"]) not in seen]
        routes = exact + base
        if not routes:
            if self._unknown_fallback and model != self._unknown_fallback:
                log.warning("Unknown model %r requested; falling back to %r", model, self._unknown_fallback)
                return self.routes_for(self._unknown_fallback, token)
            raise UnknownModelError(
                f"Model {model!r} is not served by any ALCF cluster. "
                "Run `alcf-proxy models` to list available models.")
        # Aliases of one logical model: ordering is purely cluster priority.
        routes.sort(key=lambda e: self._prio(e["cluster"]))
        return [dict(e) for e in routes]

    def selector_for(self, model: str, token: str) -> EndpointSelector:
        """Cached per-model EndpointSelector (keeps sticky failover state across requests).

        Rebuilt automatically if the routing table changes for this model.
        """
        routes = self.routes_for(model, token)
        key = normalize_model_name(model).casefold()
        sig = tuple((e["cluster"], e["framework"], e["model"]) for e in routes)
        with self._lock:
            cached = self._selectors.get(key)
            if cached is None or cached[0] != sig:
                self._selectors[key] = (sig, EndpointSelector(routes))
            return self._selectors[key][1]

    def models(self, token: str) -> list[dict]:
        """Unified model pool in OpenAI /v1/models shape entries."""
        table = self._ensure_table(token)
        out, seen = [], set()
        for e in table:
            if e["model"] in seen:
                continue
            seen.add(e["model"])
            out.append({"id": e["model"], "object": "model",
                        "owned_by": f"{e['cluster']}/{e['framework']}"})
        return out
