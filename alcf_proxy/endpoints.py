"""ALCF endpoint URLs and model listing."""
import httpx

from . import config

ALCF_API_ROOT = "https://inference-api.alcf.anl.gov/resource_server"


def base_url(cluster: str, framework: str) -> str:
    return f"{ALCF_API_ROOT}/{cluster}/{framework}/v1"


def chat_url(cluster: str, framework: str) -> str:
    return f"{base_url(cluster, framework)}/chat/completions"


def _parse_list_endpoints(payload: dict) -> list[str]:
    out: list[str] = []
    for cluster, cval in (payload.get("clusters") or {}).items():
        for fw, fval in (cval.get("frameworks") or {}).items():
            for m in fval.get("models") or []:
                name = m if isinstance(m, str) else (m.get("id") or m.get("name") or str(m))
                out.append(f"{cluster}/{fw}: {name}")
    return out


def list_models(token: str) -> list[str]:
    url = f"{ALCF_API_ROOT}/list-endpoints"
    r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return _parse_list_endpoints(r.json())
