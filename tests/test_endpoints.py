import json
from alcf_proxy import endpoints


def test_chat_url():
    assert endpoints.chat_url("sophia", "vllm").endswith("/sophia/vllm/v1/chat/completions")


def test_base_url():
    assert endpoints.base_url("metis", "api").endswith("/metis/api/v1")


def test_parse_list_endpoints(fixtures_dir):
    payload = json.loads((fixtures_dir / "list_endpoints.json").read_text())
    models = endpoints._parse_list_endpoints(payload)
    assert isinstance(models, list) and models
    assert any("sophia/vllm" in m for m in models)
