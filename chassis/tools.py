from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Protocol


@dataclass
class ToolResult:
    ok: bool
    data: Any = None
    error: str | None = None


class Tool(Protocol):
    name: str

    def run(self, **kwargs: Any) -> ToolResult: ...


class FunctionTool:
    def __init__(self, name: str, fn: Callable[..., Any]):
        self.name = name
        self._fn = fn

    def run(self, **kwargs: Any) -> ToolResult:
        try:
            return ToolResult(ok=True, data=self._fn(**kwargs))
        except Exception as exc:  # noqa: BLE001 — surface to audit
            return ToolResult(ok=False, error=str(exc))
