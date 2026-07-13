"""Registry mapping frontend endpoint paths to their translation/sanitize spec."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .sanitizers import sanitize_chat


@dataclass(frozen=True)
class FormatSpec:
    name: str            # llm-rosetta frontend key: "chat" | "responses" | "anthropic"
    sanitize: Callable[[dict], dict]


FORMATS = {
    "/v1/chat/completions": FormatSpec("chat", sanitize_chat),
    "/v1/responses": FormatSpec("responses", sanitize_chat),
    "/v1/messages": FormatSpec("anthropic", sanitize_chat),
}
