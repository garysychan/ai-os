"""Typed contract for objects that declare governed Tool metadata."""

from typing import Protocol

from .models import ToolMetadata


class Tool(Protocol):
    @property
    def metadata(self) -> ToolMetadata: ...
