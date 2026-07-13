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
}
_ENV_PREFIX = "ALCF_PROXY_"
_INT_KEYS = {"port"}
_BOOL_KEYS = {"verbose"}


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

    @property
    def auth_script(self) -> str:
        return auth_script_path()


def config_search_paths() -> list[str]:
    return ["./config.yaml", os.path.join(user_config_dir("alcf-proxy"), "config.yaml")]


def _coerce(key, val):
    if key in _INT_KEYS:
        return int(val)
    if key in _BOOL_KEYS:
        return str(val).lower() in ("1", "true", "yes", "on")
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


def auth_script_path() -> str:
    return os.path.expanduser(
        os.environ.get(_ENV_PREFIX + "AUTH_SCRIPT", "~/inference_auth_token.py")
    )
