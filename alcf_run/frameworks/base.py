"""Framework abstraction."""
from __future__ import annotations


class Framework:
    name: str = "base"

    def run(self, argv: list[str]) -> int:  # pragma: no cover - interface
        raise NotImplementedError
