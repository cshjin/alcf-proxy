import pytest

from alcf_proxy import router as router_mod
from alcf_proxy.router import ModelRouter, UnknownModelError

PAYLOAD = {
    "clusters": {
        "sophia": {"frameworks": {"vllm": {"models": [
            "openai/gpt-oss-120b", "meta-llama/Llama-3.3-70B-Instruct"]}}},
        "metis": {"frameworks": {"api": {"models": ["gpt-oss-120b"]}}},
        "minerva": {"frameworks": {"api": {"models": ["nemotron-3-ultra"]}}},
    }
}


def _mk(payload=PAYLOAD, ttl_s=3600, priority=("sophia", "metis", "minerva"), fail=False,
        backoff=0):
    state = {"fetches": 0}

    def fetch(token):
        state["fetches"] += 1
        if fail:
            raise RuntimeError("gateway down")
        return payload

    r = ModelRouter(cluster_priority=priority, ttl_s=ttl_s, retry_backoff_s=backoff, fetch=fetch)
    return r, state


def test_exact_id_routes_with_basename_fallbacks():
    r, _ = _mk()
    routes = r.routes_for("openai/gpt-oss-120b", "T")
    # sophia exact first, then metis via basename — model id remapped per endpoint
    assert routes[0] == {"cluster": "sophia", "framework": "vllm", "model": "openai/gpt-oss-120b"}
    assert routes[1] == {"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"}


def test_basename_query_finds_all_hosts_priority_ordered():
    r, _ = _mk()
    routes = r.routes_for("gpt-oss-120b", "T")
    assert [x["cluster"] for x in routes] == ["sophia", "metis"]
    assert routes[0]["model"] == "openai/gpt-oss-120b"  # local id on sophia


def test_casefold_matching():
    r, _ = _mk()
    routes = r.routes_for("GPT-OSS-120B", "T")
    assert routes, "casefold match failed"


def test_custom_priority_flips_order():
    r, _ = _mk(priority=("metis", "sophia", "minerva"))
    routes = r.routes_for("gpt-oss-120b", "T")
    assert [x["cluster"] for x in routes] == ["metis", "sophia"]


def test_unknown_model_raises():
    r, _ = _mk()
    with pytest.raises(UnknownModelError):
        r.routes_for("does-not-exist", "T")


def test_ttl_no_refetch_within_window():
    r, state = _mk(ttl_s=3600)
    r.routes_for("gpt-oss-120b", "T")
    r.routes_for("nemotron-3-ultra", "T")
    assert state["fetches"] == 1


def test_ttl_expiry_refetches():
    r, state = _mk(ttl_s=0)
    r.routes_for("gpt-oss-120b", "T")
    r.routes_for("gpt-oss-120b", "T")
    assert state["fetches"] >= 2


def test_refresh_failure_keeps_stale_table():
    state = {"fetches": 0}

    def fetch(token):
        state["fetches"] += 1
        if state["fetches"] > 1:
            raise RuntimeError("gateway down")
        return PAYLOAD

    r = ModelRouter(ttl_s=0, fetch=fetch)
    assert r.routes_for("gpt-oss-120b", "T")
    # second call: refresh fails but stale table still serves
    assert r.routes_for("gpt-oss-120b", "T")


def test_fetch_failure_with_no_table_propagates():
    r, _ = _mk(fail=True)
    with pytest.raises(RuntimeError):
        r.routes_for("gpt-oss-120b", "T")


def test_refresh_attempts_are_backoff_throttled():
    # A slow/broken catalog must not be re-hit on every request: after any attempt, further
    # refresh attempts wait out retry_backoff_s (stale table keeps serving meanwhile).
    r, state = _mk(ttl_s=0, backoff=60)
    r.routes_for("gpt-oss-120b", "T")
    r.routes_for("gpt-oss-120b", "T")
    r.routes_for("nemotron-3-ultra", "T")
    assert state["fetches"] == 1


def test_gateway_auth_error_surfaces_even_with_stale_table():
    from alcf_proxy.endpoints import GatewayAuthError
    state = {"fetches": 0}

    def fetch(token):
        state["fetches"] += 1
        if state["fetches"] > 1:
            raise GatewayAuthError("30-day policy: re-auth required")
        return PAYLOAD

    r = ModelRouter(ttl_s=0, retry_backoff_s=0, fetch=fetch)
    r.routes_for("gpt-oss-120b", "T")
    with pytest.raises(GatewayAuthError):
        r.routes_for("gpt-oss-120b", "T")


def test_basename_collision_of_distinct_models_logs_warning(caplog):
    import logging
    payload = {"clusters": {
        "sophia": {"frameworks": {"vllm": {"models": ["orgA/foo"]}}},
        "metis": {"frameworks": {"api": {"models": ["orgB/foo"]}}},
    }}
    r, _ = _mk(payload=payload)
    with caplog.at_level(logging.WARNING, logger="alcf_proxy.router"):
        r.routes_for("orgA/foo", "T")
    assert any("foo" in rec.message and "distinct" in rec.message for rec in caplog.records)


def test_prefix_alias_same_model_does_not_warn(caplog):
    import logging
    with caplog.at_level(logging.WARNING, logger="alcf_proxy.router"):
        r, _ = _mk()
        r.routes_for("gpt-oss-120b", "T")
    assert not [rec for rec in caplog.records if "distinct" in rec.message]


def test_models_unified_pool_openai_shape():
    r, _ = _mk()
    pool = r.models("T")
    ids = [m["id"] for m in pool]
    assert "openai/gpt-oss-120b" in ids and "nemotron-3-ultra" in ids
    assert all("owned_by" in m for m in pool)


def test_selector_for_is_cached_and_sticky_capable():
    r, _ = _mk()
    s1 = r.selector_for("gpt-oss-120b", "T")
    s2 = r.selector_for("gpt-oss-120b", "T")
    assert s1 is s2  # cached -> sticky state survives across requests
    assert s1.active()["cluster"] == "sophia"


def test_context_window_suffix_and_aliases():
    payload = {
        "clusters": {
            "minerva": {"frameworks": {"api": {"models": ["inkling-bf16"]}}},
            "sophia": {"frameworks": {"vllm": {"models": ["openai/gpt-oss-120b"]}}},
        }
    }
    r, _ = _mk(payload=payload)
    # [1m] context window suffix (Claude Code style)
    routes = r.routes_for("inkling-bf16[1m]", "T")
    assert routes[0]["model"] == "inkling-bf16"
    assert routes[0]["cluster"] == "minerva"

    # [200k] suffix
    routes2 = r.routes_for("openai/gpt-oss-120b[200k]", "T")
    assert routes2[0]["model"] == "openai/gpt-oss-120b"

    # alcf: provider prefix
    routes3 = r.routes_for("alcf:inkling-bf16", "T")
    assert routes3[0]["model"] == "inkling-bf16"

    # inkling alias -> inkling-bf16
    routes4 = r.routes_for("inkling", "T")
    assert routes4[0]["model"] == "inkling-bf16"


def test_unknown_model_fallback():
    payload = {
        "clusters": {
            "minerva": {"frameworks": {"api": {"models": ["inkling-bf16"]}}},
        }
    }
    def fetch(token):
        return payload
    r = ModelRouter(fetch=fetch, unknown_model_fallback="inkling-bf16")
    routes = r.routes_for("claude-3-5-sonnet-20241022", "T")
    assert routes[0]["model"] == "inkling-bf16"

