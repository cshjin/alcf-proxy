import os
import yaml
from alcf_proxy import config


def test_defaults_when_no_file(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(config, "config_search_paths", lambda: [str(tmp_path / "none.yaml")])
    cfg = config.load_config()
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 11445
    assert cfg.cluster == "sophia"
    assert cfg.default_model == "openai/gpt-oss-120b"


def test_yaml_overrides_defaults(tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump({"port": 8080, "cluster": "metis", "framework": "api"}))
    monkeypatch.setattr(config, "config_search_paths", lambda: [str(p)])
    cfg = config.load_config()
    assert cfg.port == 8080
    assert cfg.cluster == "metis"
    assert cfg.framework == "api"
    assert cfg.host == "127.0.0.1"


def test_env_overrides_yaml(tmp_path, monkeypatch):
    p = tmp_path / "config.yaml"
    p.write_text(yaml.safe_dump({"port": 8080}))
    monkeypatch.setattr(config, "config_search_paths", lambda: [str(p)])
    monkeypatch.setenv("ALCF_PROXY_PORT", "9090")
    cfg = config.load_config()
    assert cfg.port == 9090


def test_cli_overrides_all(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "config_search_paths", lambda: [])
    monkeypatch.setenv("ALCF_PROXY_PORT", "9090")
    cfg = config.load_config(cli_overrides={"port": 7070})
    assert cfg.port == 7070


def test_init_config_writes_yaml(tmp_path):
    p = tmp_path / "sub" / "config.yaml"
    config.init_config(str(p), {"port": 1234})
    loaded = yaml.safe_load(p.read_text())
    assert loaded["port"] == 1234


def test_auth_script_env_override(monkeypatch):
    monkeypatch.setenv("ALCF_PROXY_AUTH_SCRIPT", "/tmp/x.py")
    assert config.auth_script_path() == "/tmp/x.py"


def test_endpoints_synthesized_from_primary_plus_defaults():
    cfg = config.Config({"cluster": "sophia", "framework": "vllm",
                         "default_model": "openai/gpt-oss-120b"})
    eps = cfg.endpoints()
    assert eps[0] == {"cluster": "sophia", "framework": "vllm", "model": "openai/gpt-oss-120b"}
    # metis fallback present, model name without openai/ prefix
    assert any(e["cluster"] == "metis" and e["model"] == "gpt-oss-120b" for e in eps)


def test_endpoints_primary_not_duplicated_in_defaults():
    # if primary IS the metis default, it must appear once (as primary)
    cfg = config.Config({"cluster": "metis", "framework": "api", "default_model": "gpt-oss-120b"})
    eps = cfg.endpoints()
    metis = [e for e in eps if e["cluster"] == "metis" and e["framework"] == "api"]
    assert len(metis) == 1
    assert eps[0]["cluster"] == "metis"


def test_endpoints_explicit_list_used_verbatim():
    cfg = config.Config({"endpoints": [
        {"cluster": "metis", "framework": "api", "model": "gpt-oss-120b"},
        {"cluster": "sophia", "framework": "vllm", "model": "openai/gpt-oss-120b"},
    ]})
    eps = cfg.endpoints()
    assert len(eps) == 2
    assert eps[0]["cluster"] == "metis"
    assert eps[1]["cluster"] == "sophia"
