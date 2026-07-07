"""Shared constants and environment resolution for alcf-run."""
import os

DEFAULT_MODEL = "openai/gpt-oss-120b"
DEFAULT_CLUSTER = "sophia"
DEFAULT_FRAMEWORK = "vllm"
DEFAULT_PROXY_PORT = 11445  # avoid argo's 11444
ALCF_API_ROOT = "https://inference-api.alcf.anl.gov/resource_server"
PROVIDER_NAME = "alcf_proxy"  # codex provider key we manage
DEFAULT_PROFILE = "alcf-gpt-oss-120b"


def auth_script_path() -> str:
    """Path to inference_auth_token.py; overridable via ALCF_AUTH_SCRIPT."""
    return os.path.expanduser(os.environ.get("ALCF_AUTH_SCRIPT", "~/inference_auth_token.py"))


def codex_home() -> str:
    """Locate codex config dir: $CODEX_HOME, else $SCRATCH/.codex, else ~/.codex."""
    if os.environ.get("CODEX_HOME"):
        return os.environ["CODEX_HOME"]
    scratch = os.environ.get("SCRATCH")
    if scratch:
        return os.path.join(scratch, ".codex")
    return os.path.expanduser("~/.codex")
