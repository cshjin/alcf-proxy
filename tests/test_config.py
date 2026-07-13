from alcf_proxy import config


def test_defaults():
    assert config.DEFAULT_MODEL == "openai/gpt-oss-120b"
    assert config.DEFAULT_PROXY_PORT == 11445
    assert config.PROVIDER_NAME == "alcf_proxy"


def test_auth_script_env_override(monkeypatch):
    monkeypatch.setenv("ALCF_AUTH_SCRIPT", "/tmp/foo.py")
    assert config.auth_script_path() == "/tmp/foo.py"


def test_codex_home_prefers_env(monkeypatch):
    monkeypatch.setenv("CODEX_HOME", "/tmp/ch")
    assert config.codex_home() == "/tmp/ch"


def test_codex_home_scratch_fallback(monkeypatch):
    monkeypatch.delenv("CODEX_HOME", raising=False)
    monkeypatch.setenv("SCRATCH", "/tmp/scr")
    assert config.codex_home() == "/tmp/scr/.codex"
