import tomllib
from alcf_run.frameworks import codex


ARGO_CONFIG = """\
model = "gpt-5.5"
model_provider = "argo"

[model_providers.argo]
name = "Argo Proxy"
base_url = "http://localhost:11444/v1"
wire_api = "responses"

[projects."/some/path"]
trust_level = "trusted"
"""


def test_merge_adds_alcf_provider_only():
    doc = tomllib.loads(ARGO_CONFIG)
    merged = codex._merge_provider(doc, "http://localhost:11445/v1")
    # argo untouched
    assert merged["model"] == "gpt-5.5"
    assert merged["model_provider"] == "argo"
    assert merged["model_providers"]["argo"]["base_url"] == "http://localhost:11444/v1"
    assert merged["projects"]["/some/path"]["trust_level"] == "trusted"
    # alcf_proxy added
    ap = merged["model_providers"]["alcf_proxy"]
    assert ap["base_url"] == "http://localhost:11445/v1"
    assert ap["wire_api"] == "responses"
    assert "env_key" not in ap  # token injected by proxy, not codex


def test_ensure_provider_config_writes_and_backs_up(tmp_path):
    ch = tmp_path
    (ch / "config.toml").write_text(ARGO_CONFIG)
    codex.ensure_provider_config(str(ch), "http://localhost:11445/v1")
    # backup exists
    assert (ch / "config.toml.alcf-run.bak").exists()
    # base config still parses and argo intact
    doc = tomllib.loads((ch / "config.toml").read_text())
    assert doc["model_providers"]["argo"]["base_url"] == "http://localhost:11444/v1"
    assert doc["model_providers"]["alcf_proxy"]["base_url"] == "http://localhost:11445/v1"
    # base config must NOT contain a [profiles.*] table (codex >=0.142 hard error)
    assert "profiles" not in doc
    # profile file written separately
    prof = ch / "alcf-gpt-oss-120b.config.toml"
    assert prof.exists()
    pdoc = tomllib.loads(prof.read_text())
    assert pdoc["model"] == "openai/gpt-oss-120b"
    assert pdoc["model_provider"] == "alcf_proxy"


def test_ensure_provider_config_idempotent(tmp_path):
    ch = tmp_path
    (ch / "config.toml").write_text(ARGO_CONFIG)
    codex.ensure_provider_config(str(ch), "http://localhost:11445/v1")
    first = (ch / "config.toml").read_text()
    codex.ensure_provider_config(str(ch), "http://localhost:11445/v1")
    second = (ch / "config.toml").read_text()
    assert first == second  # no churn on repeat
