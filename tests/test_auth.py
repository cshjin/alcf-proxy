import pytest
from alcf_proxy import auth


def _patch(monkeypatch, token="TOK123", secs=40 * 3600, exists=True, fail=False):
    """Patch the in-process alcf_auth engine so no globus_sdk / network is touched."""
    state = {"fetches": 0}

    def fake_access_token(app=None):
        state["fetches"] += 1
        if fail:
            raise RuntimeError("globus boom")
        return token

    monkeypatch.setattr(auth.alcf_auth, "access_token", fake_access_token)
    monkeypatch.setattr(auth.alcf_auth, "seconds_until_expiry", lambda app=None: secs)
    monkeypatch.setattr(auth.alcf_auth, "tokens_exist", lambda app=None: exists)
    return state


def test_get_valid_token_returns_token(monkeypatch):
    _patch(monkeypatch)
    tm = auth.TokenManager()
    assert tm.get_valid_token() == "TOK123"


def test_reuses_token_within_margin(monkeypatch):
    state = _patch(monkeypatch, secs=40 * 3600)
    tm = auth.TokenManager()
    tm.get_valid_token()
    tm.get_valid_token()
    assert state["fetches"] == 1  # second call reuses cached token


def test_refresh_when_near_expiry(monkeypatch):
    state = _patch(monkeypatch, secs=30)  # < 300s margin
    tm = auth.TokenManager(refresh_margin_s=300)
    tm.get_valid_token()
    tm.get_valid_token()
    assert state["fetches"] >= 2  # near expiry -> refetch


def test_fetch_failure_raises_autherror(monkeypatch):
    _patch(monkeypatch, fail=True)
    tm = auth.TokenManager()
    with pytest.raises(auth.AuthError):
        tm.get_valid_token()


def test_fetch_failure_mentions_authenticate(monkeypatch):
    _patch(monkeypatch, fail=True)
    tm = auth.TokenManager()
    try:
        tm.get_valid_token()
    except auth.AuthError as e:
        assert "authenticate" in str(e).lower()


def test_hours_left(monkeypatch):
    _patch(monkeypatch, secs=12.5 * 3600)
    tm = auth.TokenManager()
    assert tm.hours_left() == pytest.approx(12.5, abs=0.01)


def test_hours_left_none_on_error(monkeypatch):
    _patch(monkeypatch)
    monkeypatch.setattr(auth.alcf_auth, "seconds_until_expiry",
                        lambda app=None: (_ for _ in ()).throw(RuntimeError("no token")))
    tm = auth.TokenManager()
    assert tm.hours_left() is None
