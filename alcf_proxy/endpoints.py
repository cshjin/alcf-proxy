"""ALCF endpoint URL construction and model listing."""
import httpx

from . import config


def base_url(cluster: str, framework: str) -> str:
    return f"{config.ALCF_API_ROOT}/{cluster}/{framework}/v1"


def responses_url(cluster: str, framework: str) -> str:
    return f"{base_url(cluster, framework)}/responses"


def _parse_list_endpoints(payload: dict) -> list[str]:
    """Flatten the list-endpoints payload into 'cluster/fw: model' strings (FACT 4)."""
    out: list[str] = []
    for cluster, cval in (payload.get("clusters") or {}).items():
        for fw, fval in (cval.get("frameworks") or {}).items():
            models = fval.get("models") or []
            for m in models:
                name = m if isinstance(m, str) else (m.get("id") or m.get("name") or str(m))
                out.append(f"{cluster}/{fw}: {name}")
    return out


def list_models(token: str) -> list[str]:
    url = f"{config.ALCF_API_ROOT}/list-endpoints"
    r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    r.raise_for_status()
    return _parse_list_endpoints(r.json())
