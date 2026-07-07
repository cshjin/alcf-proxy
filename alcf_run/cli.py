"""Unified CLI: alcf-run <framework|command> [args...]."""
from __future__ import annotations

import argparse
import sys

from . import auth, endpoints
from .frameworks.codex import CodexFramework


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    parser = argparse.ArgumentParser(prog="alcf-run", add_help=True)
    parser.add_argument("command", help="codex | models | auth | claude")
    ns, rest = parser.parse_known_args(argv)

    if ns.command == "codex":
        return CodexFramework().run(rest)
    if ns.command == "claude":
        print("alcf-run: 'claude' framework not yet implemented")
        return 0
    if ns.command == "models":
        try:
            for m in endpoints.list_models(auth.get_token()):
                print(m)
            return 0
        except Exception as e:
            print(f"alcf-run: {e}", file=sys.stderr)
            return 1
    if ns.command == "auth":
        try:
            hrs = auth.token_hours_left()
            tok = auth.get_token()
            print(f"alcf-run: token OK ({len(tok)} chars), ~{hrs}h left" if hrs
                  else f"alcf-run: token OK ({len(tok)} chars)")
            return 0
        except Exception as e:
            print(f"alcf-run: {e}", file=sys.stderr)
            return 1

    print(f"alcf-run: unknown command '{ns.command}'", file=sys.stderr)
    return 2
