import subprocess
import pytest
from alcf_proxy import auth


def test_get_token_uses_sys_executable(monkeypatch):
    calls = {}

    def fake_run(cmd, **kwargs):
        calls["cmd"] = cmd
        class R:
            returncode = 0
            stdout = "TOKEN123\n"
            stderr = ""
        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    tok = auth.get_token()
    assert tok == "TOKEN123"
    # must invoke the auth script with the current interpreter, not bare "python3"
    import sys
    assert calls["cmd"][0] == sys.executable
    assert calls["cmd"][2] == "get_access_token"


def test_get_token_failure_raises_autherror(monkeypatch):
    def fake_run(cmd, **kwargs):
        class R:
            returncode = 1
            stdout = ""
            stderr = "ModuleNotFoundError: globus_sdk"
        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    with pytest.raises(auth.AuthError):
        auth.get_token()


def test_token_hours_left_parses_float(monkeypatch):
    def fake_run(cmd, **kwargs):
        class R:
            returncode = 0
            stdout = "40.84\n"
            stderr = ""
        return R()

    monkeypatch.setattr(subprocess, "run", fake_run)
    assert auth.token_hours_left() == pytest.approx(40.84)
