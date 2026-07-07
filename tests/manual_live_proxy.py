"""Manual live smoke test for the ALCF proxy (NOT run under pytest).

Starts the ephemeral proxy, then POSTs a streaming responses request exactly like codex would.
Confirms the proxy forwards to ALCF as stream:false and re-wraps the reply as SSE.

Run: /pscratch/sd/j/jinh/envs/hack/bin/python tests/manual_live_proxy.py
"""
import httpx

from alcf_run.proxy.manager import ProxyManager

mgr = ProxyManager("sophia", "vllm")
port = mgr.start()
try:
    r = httpx.post(
        f"http://127.0.0.1:{port}/v1/responses",
        json={"model": "openai/gpt-oss-120b", "input": "say hi", "stream": True},
        timeout=300,
    )
    print("STATUS", r.status_code)
    print(r.text[:1500])
finally:
    mgr.stop()
