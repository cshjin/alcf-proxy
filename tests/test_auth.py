import sys
import subprocess
import pytest
from alcf_proxy import auth


def _mk(monkeypatch, token="TOK123", hours="40.0", rc=0):
    calls = []
    def fake_run(cmd, **kw):
        calls.append(cmd)
        sub = cmd[2]
        class R:
            returncode = rc
            stderr = "" if rc == 0 else "boom"
            stdout = token if sub == "get_access_token" else hours
        return R()
    monkeypatch.setattr(subprocess, "run", fake_run)
    return calls


def test_fetch_uses_sys_executable(monkeypatch):
    calls = _mk(monkeypatch)
    tm = auth.TokenManager()
    assert tm.get_valid_token() == "TOK123"
    assert calls[0][0] == sys.executable
    assert calls[0][2] == "get_access_token"


def test_reuses_token_within_margin(monkeypatch):
    calls = _mk(monkeypatch, hours="40.0")
    tm = auth.TokenManager()
    tm.get_valid_token()
    tm.get_valid_token()
    fetches = [c for c in calls if c[2] == "get_access_token"]
    assert len(fetches) == 1


def test_refresh_when_near_expiry(monkeypatch):
    calls = _mk(monkeypatch, hours="0.01")
    tm = auth.TokenManager(refresh_margin_s=300)
    tm.get_valid_token()
    tm.get_valid_token()
    fetches = [c for c in calls if c[2] == "get_access_token"]
    assert len(fetches) >= 2


def test_fetch_failure_raises_autherror(monkeypatch):
    _mk(monkeypatch, rc=1)
    tm = auth.TokenManager()
    with pytest.raises(auth.AuthError):
        tm.get_valid_token()


def test_hours_left_parses(monkeypatch):
    _mk(monkeypatch, hours="12.5")
    tm = auth.TokenManager()
    assert tm.hours_left() == pytest.approx(12.5)
