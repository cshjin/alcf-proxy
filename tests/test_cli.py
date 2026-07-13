from alcf_proxy import cli


def test_models_command(monkeypatch, capsys):
    monkeypatch.setattr("alcf_proxy.cli.auth.TokenManager.get_valid_token", lambda self: "T")
    monkeypatch.setattr("alcf_proxy.cli.endpoints.list_models",
                        lambda tok: ["sophia/vllm: openai/gpt-oss-120b"])
    rc = cli.main(["models"])
    assert rc == 0
    assert "gpt-oss-120b" in capsys.readouterr().out


def test_health_command(monkeypatch, capsys):
    monkeypatch.setattr("alcf_proxy.cli.auth.TokenManager.hours_left", lambda self: 40.0)
    rc = cli.main(["health"])
    assert rc == 0
    assert "40" in capsys.readouterr().out


def test_config_show(monkeypatch, capsys):
    rc = cli.main(["config", "show"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "port" in out


def test_serve_invokes_uvicorn(monkeypatch):
    called = {}
    monkeypatch.setattr("alcf_proxy.cli.uvicorn.run",
                        lambda app, **kw: called.update(kw))
    monkeypatch.setattr("alcf_proxy.cli.auth.TokenManager.get_valid_token", lambda self: "T")
    rc = cli.main(["serve", "--port", "9999"])
    assert rc == 0
    assert called["port"] == 9999


def test_serve_refuses_nonloopback_without_key(monkeypatch, capsys):
    # C4: binding to a non-loopback host exposes the injected ALCF token to the network; refuse
    # unless a proxy API key is configured.
    monkeypatch.setattr("alcf_proxy.cli.auth.TokenManager.get_valid_token", lambda self: "T")
    started = {"ran": False}
    monkeypatch.setattr("alcf_proxy.cli.uvicorn.run",
                        lambda app, **kw: started.update(ran=True))
    rc = cli.main(["serve", "--host", "0.0.0.0"])
    assert rc != 0
    assert not started["ran"]
    assert "loopback" in capsys.readouterr().err.lower() or "0.0.0.0" in capsys.readouterr().err


def test_serve_allows_nonloopback_with_key(monkeypatch):
    monkeypatch.setattr("alcf_proxy.cli.auth.TokenManager.get_valid_token", lambda self: "T")
    called = {}
    monkeypatch.setattr("alcf_proxy.cli.uvicorn.run", lambda app, **kw: called.update(kw))
    monkeypatch.setenv("ALCF_PROXY_API_KEY", "secret")
    rc = cli.main(["serve", "--host", "0.0.0.0", "--port", "8080"])
    assert rc == 0
    assert called["host"] == "0.0.0.0"


def test_auth_status(monkeypatch, capsys):
    monkeypatch.setattr("alcf_proxy.cli.alcf_auth.tokens_exist", lambda: True)
    monkeypatch.setattr("alcf_proxy.cli.alcf_auth.token_filepath", lambda: "/x/tokens.json")
    monkeypatch.setattr("alcf_proxy.cli.auth.TokenManager.hours_left", lambda self: 40.0)
    rc = cli.main(["auth", "status"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "authenticated" in out and "40" in out


def test_auth_login_invokes_authenticate(monkeypatch, capsys):
    called = {"n": 0}
    monkeypatch.setattr("alcf_proxy.cli.alcf_auth.authenticate",
                        lambda: called.update(n=called["n"] + 1))
    monkeypatch.setattr("alcf_proxy.cli.alcf_auth.token_filepath", lambda: "/x/tokens.json")
    rc = cli.main(["auth", "login"])
    assert rc == 0
    assert called["n"] == 1
    assert "authenticated" in capsys.readouterr().out.lower()


def test_unknown_command_errors():
    assert cli.main(["nonsense"]) != 0
