"""Codex framework: merge an alcf_proxy provider into the codex config (add-only, argo untouched),
start an ephemeral proxy, and exec codex.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import tomllib

import tomli_w

from .. import config
from .base import Framework


def _merge_provider(doc: dict, proxy_base_url: str) -> dict:
    """Return doc with [model_providers.alcf_proxy] set. Never touches other keys."""
    providers = doc.setdefault("model_providers", {})
    providers[config.PROVIDER_NAME] = {
        "name": "ALCF (via alcf-run proxy)",
        "base_url": proxy_base_url,
        "wire_api": "responses",
    }
    return doc


def ensure_provider_config(codex_home: str, proxy_base_url: str) -> None:
    cfg_path = os.path.join(codex_home, "config.toml")
    os.makedirs(codex_home, exist_ok=True)
    doc = {}
    if os.path.exists(cfg_path):
        with open(cfg_path, "rb") as f:
            doc = tomllib.load(f)

    # Idempotency: skip write if already correct.
    existing = doc.get("model_providers", {}).get(config.PROVIDER_NAME)
    want = {"name": "ALCF (via alcf-run proxy)", "base_url": proxy_base_url, "wire_api": "responses"}
    if existing != want:
        if os.path.exists(cfg_path):
            shutil.copy2(cfg_path, cfg_path + ".alcf-run.bak")
        _merge_provider(doc, proxy_base_url)
        with open(cfg_path, "wb") as f:
            tomli_w.dump(doc, f)

    # Profile file (codex >=0.142: separate file, top-level keys, no [profiles.*] table).
    prof_path = os.path.join(codex_home, f"{config.DEFAULT_PROFILE}.config.toml")
    prof = {"model": config.DEFAULT_MODEL, "model_provider": config.PROVIDER_NAME}
    prof_bytes = tomli_w.dumps(prof).encode()
    if not os.path.exists(prof_path) or open(prof_path, "rb").read() != prof_bytes:
        with open(prof_path, "wb") as f:
            f.write(prof_bytes)


class CodexFramework(Framework):
    name = "codex"

    def run(self, argv: list[str]) -> int:
        from ..proxy.manager import ProxyManager
        from .. import auth

        hours = auth.token_hours_left()
        if hours is not None:
            print(f"alcf-run: ALCF token valid for ~{hours:.1f}h "
                  f"(restart if it expires mid-session)", flush=True)

        ch = config.codex_home()
        mgr = ProxyManager(config.DEFAULT_CLUSTER, config.DEFAULT_FRAMEWORK)
        port = mgr.start()
        try:
            ensure_provider_config(ch, f"http://localhost:{port}/v1")
            cmd = ["codex"]
            if "--profile" not in argv and "-p" not in argv:
                cmd += ["--profile", config.DEFAULT_PROFILE]
            cmd += argv
            env = dict(os.environ, CODEX_HOME=ch)
            return subprocess.call(cmd, env=env)
        finally:
            mgr.stop()
