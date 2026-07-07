from alcf_run import cli


def test_claude_stub(capsys):
    rc = cli.main(["claude"])
    assert rc == 0
    assert "not yet implemented" in capsys.readouterr().out.lower()


def test_models_lists(monkeypatch, capsys):
    monkeypatch.setattr("alcf_run.auth.get_token", lambda: "TOK")
    monkeypatch.setattr("alcf_run.endpoints.list_models", lambda tok: ["sophia/vllm: openai/gpt-oss-120b"])
    rc = cli.main(["models"])
    assert rc == 0
    assert "gpt-oss-120b" in capsys.readouterr().out


def test_codex_dispatches(monkeypatch):
    called = {}

    def fake_run(self, argv):
        called["argv"] = argv
        return 0

    monkeypatch.setattr("alcf_run.frameworks.codex.CodexFramework.run", fake_run)
    rc = cli.main(["codex", "hello"])
    assert rc == 0
    assert called["argv"] == ["hello"]


def test_unknown_command_errors():
    rc = cli.main(["nonsense"])
    assert rc != 0
