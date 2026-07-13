"""ALCF token management via inference_auth_token.py.

Runs the auth script with the CURRENT interpreter (sys.executable), because only the environment
alcf-run is installed in has globus_sdk (see _hj verified facts, FACT 1). A bare "python3" would
resolve to a system interpreter without globus_sdk.
"""
import subprocess
import sys

from . import config


class AuthError(Exception):
    pass


_GUIDANCE = (
    "Failed to obtain an ALCF token. If your login expired, run:\n"
    "  {py} {script} authenticate"
)


def _run(subcmd: list[str]) -> str:
    cmd = [sys.executable, config.auth_script_path(), *subcmd]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise AuthError(
            _GUIDANCE.format(py=sys.executable, script=config.auth_script_path())
            + f"\n--- stderr ---\n{proc.stderr.strip()}"
        )
    return proc.stdout.strip()


def get_token() -> str:
    tok = _run(["get_access_token"])
    if not tok:
        raise AuthError("Auth script returned an empty token.")
    return tok


def token_hours_left() -> float | None:
    try:
        out = _run(["get_time_until_token_expiration", "--units", "hours"])
        return float(out.split()[0])
    except (AuthError, ValueError, IndexError):
        return None
