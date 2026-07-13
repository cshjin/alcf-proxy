"""Offline tests for the internalized globus auth engine.

globus_sdk itself is not exercised here (its network/browser calls belong to live/manual testing);
we test the pure glue: token-path unwrapping, existence check, and the thin wrappers that delegate
to a globus app object (injected as a fake).
"""
import types

import pytest

from alcf_proxy import alcf_auth


class _Inner:
    def __init__(self, filepath):
        self.filepath = filepath


class _ValidatingStorage:
    """Mimics ValidatingTokenStorage wrapping a concrete JSONTokenStorage (has .token_storage)."""
    def __init__(self, filepath):
        self.token_storage = _Inner(filepath)
        # no .filepath directly -> forces the unwrap path


class _FakeApp:
    def __init__(self, filepath="/home/u/.globus/app/x/inference_app/tokens.json"):
        self.token_storage = _ValidatingStorage(filepath)


def test_token_filepath_unwraps_wrapped_storage():
    app = _FakeApp("/tmp/toks.json")
    assert alcf_auth.token_filepath(app) == "/tmp/toks.json"


def test_token_filepath_direct_filepath():
    app = types.SimpleNamespace(token_storage=_Inner("/direct/toks.json"))
    assert alcf_auth.token_filepath(app) == "/direct/toks.json"


def test_token_filepath_none_when_absent():
    app = types.SimpleNamespace(token_storage=types.SimpleNamespace())
    assert alcf_auth.token_filepath(app) is None


def test_tokens_exist_true(tmp_path):
    p = tmp_path / "tokens.json"
    p.write_text("{}")
    app = _FakeApp(str(p))
    assert alcf_auth.tokens_exist(app) is True


def test_tokens_exist_false(tmp_path):
    app = _FakeApp(str(tmp_path / "missing.json"))
    assert alcf_auth.tokens_exist(app) is False


def test_access_token_delegates(monkeypatch):
    class _Auth:
        access_token = "AT"
        def ensure_valid_token(self):
            self.called = True
    monkeypatch.setattr(alcf_auth, "get_authorizer", lambda app=None: _Auth())
    assert alcf_auth.access_token() == "AT"


def test_seconds_until_expiry(monkeypatch):
    import time
    monkeypatch.setattr(alcf_auth, "get_authorizer",
                        lambda app=None: types.SimpleNamespace(expires_at=time.time() + 3600))
    secs = alcf_auth.seconds_until_expiry()
    assert 3500 < secs <= 3600


def test_get_authorizer_uses_app():
    class _App:
        def get_authorizer(self, gw):
            assert gw == alcf_auth.GATEWAY_CLIENT_ID
            return "AUTHZ"
    assert alcf_auth.get_authorizer(_App()) == "AUTHZ"


def test_constants_match_alcf():
    assert alcf_auth.AUTH_CLIENT_ID == "58fdd3bc-e1c3-4ce5-80ea-8d6b87cfb944"
    assert alcf_auth.GATEWAY_SCOPE.endswith("/action_all")
