import json
from alcf_proxy import endpoints


def test_responses_url():
    url = endpoints.responses_url("sophia", "vllm")
    assert url.endswith("/resource_server/sophia/vllm/v1/responses")


def test_base_url():
    assert endpoints.base_url("metis", "api").endswith("/metis/api/v1")


def test_parse_list_endpoints(fixtures_dir):
    payload = json.loads((fixtures_dir / "list_endpoints.json").read_text())
    models = endpoints._parse_list_endpoints(payload)
    # flattened "cluster/fw: model" entries; must be a non-empty list of strings
    assert isinstance(models, list) and models
    assert all(isinstance(m, str) for m in models)
    assert any("sophia/vllm" in m for m in models)
