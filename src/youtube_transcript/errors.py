from __future__ import annotations


class ToolError(Exception):
    def __init__(self, message: str, *, warnings: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.warnings = warnings or []
