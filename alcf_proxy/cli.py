"""alcf-proxy CLI: serve / models / health / config."""
from __future__ import annotations

import argparse
import json
import sys

import uvicorn

from . import auth, config, endpoints
from .server import build_app


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

    try:
        ns = parser.parse_args(argv)
    except SystemExit as e:
        return int(e.code) if e.code else 0

    if ns.command == "serve":
        overrides = {k: getattr(ns, k) for k in ("host", "port", "cluster", "framework", "default_model")}
        cfg = config.load_config(cli_overrides=overrides, path=ns.config)
        tm = auth.TokenManager()
        try:
            tm.get_valid_token()
        except auth.AuthError as e:
            print(str(e), file=sys.stderr)
            return 1
        app = build_app(cfg, tm)
        print(f"alcf-proxy serving on http://{cfg.host}:{cfg.port} "
              f"({cfg.cluster}/{cfg.framework})", flush=True)
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

    parser.print_help(sys.stderr)
    return 2


def yaml_dump(d: dict) -> str:
    import yaml
    return yaml.safe_dump(d, sort_keys=False)
