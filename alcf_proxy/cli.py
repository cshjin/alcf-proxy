"""alcf-proxy CLI: serve / models / health / config."""
from __future__ import annotations

import argparse
import json
import os
import sys

import uvicorn

from . import alcf_auth, auth, config, endpoints
from .server import build_app

# Only used as the pre-filled suggestion in the interactive first-run prompt below — not a default
# that's ever applied silently (see config.py: DEFAULTS["port"] is None).
PROMPT_DEFAULT_PORT = 52227


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="alcf-proxy")
    sub = parser.add_subparsers(dest="command")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--host")
    p_serve.add_argument("--port", type=int)
    p_serve.add_argument("--cluster")
    p_serve.add_argument("--framework")
    p_serve.add_argument("--model", dest="default_model")
    p_serve.add_argument("--config")

    p_models = sub.add_parser("models")
    p_models.add_argument("--json", action="store_true")

    sub.add_parser("health")

    p_cfg = sub.add_parser("config")
    p_cfg.add_argument("action", choices=["init", "show"])

    p_auth = sub.add_parser("auth")
    p_auth.add_argument("action", choices=["login", "status"])

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code else 0

    if ns.command == "serve":
        overrides = {k: getattr(ns, k) for k in ("host", "port", "cluster", "framework", "default_model")}
        cfg = config.load_config(cli_overrides=overrides, path=ns.config)
        if cfg.port is None:
            if not _interactive():
                print("alcf-proxy: no port configured. Copy .env.example to .env and set "
                      "ALCF_PROXY_PORT (or pass --port, or set `port:` in config.yaml).",
                      file=sys.stderr)
                return 1
            port = _prompt_for_port()
            if port is None:
                print("alcf-proxy: no port chosen, exiting.", file=sys.stderr)
                return 1
            saved_path = config.save_dotenv_port(port)
            print(f"alcf-proxy: saved ALCF_PROXY_PORT={port} to {saved_path} "
                  "(future runs won't ask again).")
            cfg.set_port(port)
        # Security: the proxy injects the real ALCF token for every caller. Binding to a non-loopback
        # host would expose that token to the network, so refuse unless an inbound API key is set.
        if not _is_loopback(cfg.host) and not os.environ.get("ALCF_PROXY_API_KEY"):
            print(f"alcf-proxy: refusing to bind non-loopback host {cfg.host!r} without an inbound "
                  "API key. Set ALCF_PROXY_API_KEY to allow this, or bind to 127.0.0.1.",
                  file=sys.stderr)
            return 1
        tm = auth.TokenManager()
        try:
            tm.get_valid_token()
        except auth.AuthError as e:
            print(str(e), file=sys.stderr)
            return 1
        app = build_app(cfg, tm)
        # 0.0.0.0/:: are bind addresses, not something you can curl — show a connectable host instead.
        probe_host = "localhost" if cfg.host in ("0.0.0.0", "::") else cfg.host
        print(f"alcf-proxy serving on http://{cfg.host}:{cfg.port} "
              f"({cfg.cluster}/{cfg.framework})", flush=True)
        print(f"  -> check it's up:  curl http://{probe_host}:{cfg.port}/health", flush=True)
        uvicorn.run(app, host=cfg.host, port=cfg.port,
                    log_level="info" if cfg.verbose else "warning")
        return 0

    if ns.command == "models":
        try:
            tm = auth.TokenManager()
            models = endpoints.list_models(tm.get_valid_token())
        except Exception as e:  # noqa: BLE001
            print(f"alcf-proxy: {e}", file=sys.stderr)
            return 1
        print(json.dumps(models) if ns.json else "\n".join(models))
        return 0

    if ns.command == "health":
        tm = auth.TokenManager()
        hrs = tm.hours_left()
        print(json.dumps({"token_hours_left": hrs}))
        return 0

    if ns.command == "config":
        if ns.action == "show":
            print(yaml_dump(config.load_config().as_dict()))
            return 0
        if ns.action == "init":
            paths = config.config_search_paths()
            target = paths[-1]
            config.init_config(target, {})
            print(f"wrote {target}")
            return 0

    if ns.command == "auth":
        if ns.action == "login":
            try:
                alcf_auth.authenticate()  # interactive browser flow (local server)
            except Exception as e:  # noqa: BLE001
                print(f"alcf-proxy: login failed: {e}", file=sys.stderr)
                return 1
            print("alcf-proxy: authenticated. Token stored at "
                  f"{alcf_auth.token_filepath()}")
            return 0
        if ns.action == "status":
            tm = auth.TokenManager()
            hrs = tm.hours_left()
            exists = alcf_auth.tokens_exist()
            print(json.dumps({"authenticated": exists, "token_hours_left": hrs,
                              "token_path": alcf_auth.token_filepath()}))
            return 0

    parser.print_help(sys.stderr)
    return 2


def yaml_dump(d: dict) -> str:
    import yaml
    return yaml.safe_dump(d, sort_keys=False)


def _is_loopback(host: str) -> bool:
    return host in ("127.0.0.1", "::1", "localhost")


def _interactive() -> bool:
    return sys.stdin.isatty()


def _prompt_for_port(default: int = PROMPT_DEFAULT_PORT) -> int | None:
    """First-run prompt: ask for a port, pre-filled with `default`. Returns None on Ctrl-C/EOF."""
    print("alcf-proxy: no port configured yet. (Set ALCF_PROXY_PORT in .env — see .env.example — "
          "to skip this prompt next time.)")
    try:
        raw = input(f"Port to listen on [{default}]: ").strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return None
    if not raw:
        return default
    try:
        return int(raw)
    except ValueError:
        print(f"alcf-proxy: {raw!r} is not a valid port number; using the default {default}.",
              file=sys.stderr)
        return default
