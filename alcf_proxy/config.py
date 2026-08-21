"""Configuration: YAML file + env + CLI overrides, with cross-platform search paths."""
from __future__ import annotations

import os

import yaml
from platformdirs import user_config_dir

DEFAULTS = {
    "host": "127.0.0.1",
    "port": 11445,
    "cluster": "sophia",
    "framework": "vllm",
    "default_model": "openai/gpt-oss-120b",
    "verbose": False,
    # Cluster order used by the unified model router when several clusters serve a model,
    # and by the built-in failover chain.
    "cluster_priority": ["sophia", "metis", "minerva"],
}
_ENV_PREFIX = "ALCF_PROXY_"
_INT_KEYS = {"port"}
_BOOL_KEYS = {"verbose"}
_LIST_KEYS = {"cluster_priority"}  # env override: comma-separated

# Built-in fallback chain, tried in order when a cluster is down (503/maintenance).
# Model ids differ per endpoint (sophia/vllm uses the openai/ prefix; metis/api does not).
# All three clusters serve gpt-oss-120b (verified live 2026-08-21), so the whole chain is one model.
DEFAULT_ENDPOINTS = [
    {"cluster": "sophia", "framework": "vllm", "model": "openai/gpt-oss-120b"},
    {"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"},
    {"cluster": "minerva", "framework": "api", "model": "gpt-oss-120b"},
]


class Config:
    def __init__(self, values: dict):
        self._v = dict(DEFAULTS)
        self._v.update({k: v for k, v in values.items() if v is not None})

    def __getattr__(self, name):
        try:
            return self._v[name]
        except KeyError as e:
            raise AttributeError(name) from e

    def as_dict(self) -> dict:
        return dict(self._v)

    def has_explicit_endpoints(self) -> bool:
        """True when the user pinned an explicit `endpoints:` list (bypasses the model router)."""
        return bool(self._v.get("endpoints"))

    def endpoints(self) -> list[dict]:
        """Ordered list of {cluster, framework, model} to try, primary first.

        If an explicit `endpoints` list is configured, use it verbatim. Otherwise synthesize the
        primary from cluster/framework/default_model and append the built-in fallback chain
        (deduplicated on cluster/framework so the primary is not repeated).
        """
        explicit = self._v.get("endpoints")
        if explicit:
            return [dict(e) for e in explicit]
        primary = {
            "cluster": self._v["cluster"],
            "framework": self._v["framework"],
            "model": self._v["default_model"],
        }
        result = [primary]
        for ep in DEFAULT_ENDPOINTS:
            if (ep["cluster"], ep["framework"]) != (primary["cluster"], primary["framework"]):
                result.append(dict(ep))
        return result


def config_search_paths() -> list[str]:
    return ["./config.yaml", os.path.join(user_config_dir("alcf-proxy"), "config.yaml")]


def _coerce(key, val):
    if key in _INT_KEYS:
        return int(val)
    if key in _BOOL_KEYS:
        return str(val).lower() in ("1", "true", "yes", "on")
    if key in _LIST_KEYS:
        return [x.strip() for x in str(val).split(",") if x.strip()]
    return val


def _from_env() -> dict:
    out = {}
    for key in DEFAULTS:
        env = _ENV_PREFIX + key.upper()
        if env in os.environ:
            out[key] = _coerce(key, os.environ[env])
    return out


def load_config(cli_overrides: dict | None = None, path: str | None = None) -> Config:
    values: dict = {}
    paths = [path] if path else config_search_paths()
    for p in paths:
        if p and os.path.isfile(p):
            with open(p) as f:
                values.update(yaml.safe_load(f) or {})
            break
    values.update(_from_env())
    if cli_overrides:
        values.update({k: v for k, v in cli_overrides.items() if v is not None})
    return Config(values)


def init_config(path: str, values: dict) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    merged = dict(DEFAULTS)
    merged.update(values)
    with open(path, "w") as f:
        yaml.safe_dump(merged, f, sort_keys=False)
