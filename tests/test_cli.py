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


def test_unknown_command_errors():
    assert cli.main(["nonsense"]) != 0
