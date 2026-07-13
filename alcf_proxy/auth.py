"""In-process ALCF token manager: fetch via inference_auth_token.py, refresh near expiry.

The auth script imports globus_sdk, which is only present in the interpreter alcf-proxy runs under,
so we invoke it with sys.executable (never a bare 'python3').
"""
from __future__ import annotations

import subprocess
import sys
import threading
import time

from . import config


class AuthError(Exception):
    pass


class TokenManager:
    def __init__(self, refresh_margin_s: int = 300):
        self._margin = refresh_margin_s
        self._token: str | None = None
        self._expiry_epoch: float = 0.0
        self._lock = threading.Lock()

    def _run(self, subcmd: list[str]) -> str:
        cmd = [sys.executable, config.auth_script_path(), *subcmd]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        except subprocess.TimeoutExpired as e:
            raise AuthError(f"ALCF auth script timed out after 60s: {' '.join(cmd)}") from e
        if proc.returncode != 0:
            raise AuthError(
                "ALCF auth failed. If your login expired, run:\n"
                f"  {sys.executable} {config.auth_script_path()} authenticate\n"
                f"--- stderr ---\n{proc.stderr.strip()}"
            )
        return proc.stdout.strip()

    def _fetch(self) -> str:
        tok = self._run(["get_access_token"])
        if not tok:
            raise AuthError("Auth script returned an empty token.")
        hrs = self.hours_left()
        self._token = tok
        self._expiry_epoch = time.time() + (hrs * 3600 if hrs is not None else 0)
        return tok

    def get_valid_token(self) -> str:
        with self._lock:
            if self._token is None or (self._expiry_epoch - time.time()) < self._margin:
                return self._fetch()
            return self._token

    def hours_left(self) -> float | None:
        try:
            out = self._run(["get_time_until_token_expiration", "--units", "hours"])
            return float(out.split()[0])
        except (AuthError, ValueError, IndexError):
            return None
