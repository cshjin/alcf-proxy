"""ALCF endpoint URLs, gateway catalog access, and gateway-auth error semantics."""
import httpx

from . import config

ALCF_API_ROOT = "https://inference-api.alcf.anl.gov/resource_server"

# ALCF enforces a 30-day high-assurance re-authentication policy (server-side, since ~2026-08).
# When it trips, the gateway returns 401 "Permission denied from internal policies" even though
# the local token file still looks valid (48h window). Surface actionable guidance.
REAUTH_GUIDANCE = (
    "ALCF session expired (30-day re-authentication policy). "
    "1) Logout at https://app.globus.org/logout  2) Run: alcf-proxy auth login"
)


class GatewayAuthError(Exception):
    """The gateway rejected an otherwise-valid token (high-assurance policy)."""


def policy_401(status_code: int, raw: str) -> bool:
    low = raw.lower()
    return status_code == 401 and (
        "internal policies" in low or "high-assurance" in low or "high assurance" in low
    )


def base_url(cluster: str, framework: str) -> str:
    return f"{ALCF_API_ROOT}/{cluster}/{framework}/v1"


def chat_url(cluster: str, framework: str) -> str:
    return f"{base_url(cluster, framework)}/chat/completions"


def fetch_list_endpoints(token: str) -> dict:
    """Raw list-endpoints payload: {clusters: {c: {frameworks: {f: {models: [...]}}}}}."""
    url = f"{ALCF_API_ROOT}/list-endpoints"
    r = httpx.get(url, headers={"Authorization": f"Bearer {token}"}, timeout=30)
    if policy_401(r.status_code, r.text):
        raise GatewayAuthError(f"{REAUTH_GUIDANCE}\n--- gateway said ---\n{r.text[:300]}")
    r.raise_for_status()
    return r.json()


def _parse_list_endpoints(payload: dict) -> list[str]:
    out: list[str] = []
    for cluster, cval in (payload.get("clusters") or {}).items():
        for fw, fval in (cval.get("frameworks") or {}).items():
            for m in fval.get("models") or []:
                name = m if isinstance(m, str) else (m.get("id") or m.get("name") or str(m))
                out.append(f"{cluster}/{fw}: {name}")
    return out


def list_models(token: str) -> list[str]:
    return _parse_list_endpoints(fetch_list_endpoints(token))
