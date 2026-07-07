"""Ephemeral proxy lifecycle: start uvicorn in a thread on a fixed port (fallback if taken)."""
from __future__ import annotations

import socket
import threading
import time

import httpx
import uvicorn

from .. import config
from .server import build_app


def _port_free(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(("127.0.0.1", port)) != 0


class ProxyManager:
    def __init__(self, cluster: str, framework: str, port: int = config.DEFAULT_PROXY_PORT):
        self.cluster = cluster
        self.framework = framework
        self.port = port
        self._server: uvicorn.Server | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> int:
        if not _port_free(self.port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", 0))
                self.port = s.getsockname()[1]
        app = build_app(self.cluster, self.framework)
        cfg = uvicorn.Config(app, host="127.0.0.1", port=self.port, log_level="warning")
        self._server = uvicorn.Server(cfg)
        self._thread = threading.Thread(target=self._server.run, daemon=True)
        self._thread.start()
        # wait for /health
        for _ in range(100):
            try:
                if httpx.get(f"http://127.0.0.1:{self.port}/health", timeout=1).status_code == 200:
                    return self.port
            except Exception:
                pass
            time.sleep(0.1)
        raise RuntimeError("proxy failed to start")

    def stop(self) -> None:
        if self._server:
            self._server.should_exit = True
        if self._thread:
            self._thread.join(timeout=5)

    @property
    def base_url(self) -> str:
        return f"http://localhost:{self.port}/v1"
