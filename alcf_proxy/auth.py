"""In-process ALCF token manager (cross-platform, no external script).

Uses the internalized globus_sdk auth engine in ``alcf_auth`` directly — no subprocess, no
dependency on ``~/inference_auth_token.py``, and no hard-coded token path (globus_sdk decides
where tokens live, correctly on Windows too). A valid token is cached and refreshed only when it
nears expiry.
"""
from __future__ import annotations

import threading
import time

from . import alcf_auth


class AuthError(Exception):
    pass


class TokenManager:
    def __init__(self, refresh_margin_s: int = 300):
        self._margin = refresh_margin_s
        self._token: str | None = None
        self._expiry_epoch: float = 0.0
        self._lock = threading.Lock()

    def _fetch(self) -> str:
        try:
            tok = alcf_auth.access_token()
            secs = alcf_auth.seconds_until_expiry()
        except Exception as e:  # noqa: BLE001 - globus_sdk raises many error types
            raise AuthError(
                "Failed to obtain an ALCF token. If you have never logged in, or your Globus "
                "refresh token expired (~6 months idle), authenticate with:\n"
                "  alcf-proxy auth login\n"
                f"--- cause ---\n{e}"
            ) from e
        if not tok:
            raise AuthError("ALCF auth returned an empty token.")
        self._token = tok
        self._expiry_epoch = time.time() + max(secs, 0)
        return tok

    def get_valid_token(self) -> str:
        with self._lock:
            if self._token is None or (self._expiry_epoch - time.time()) < self._margin:
                return self._fetch()
            return self._token

    def hours_left(self) -> float | None:
        try:
            return round(alcf_auth.seconds_until_expiry() / 3600, 2)
        except Exception:  # noqa: BLE001
            return None
