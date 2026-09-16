"""Explicit default-deny adapter registry."""

from __future__ import annotations

from collections.abc import Iterable

from .errors import AdapterRegistryError
from .ports import ExecutionAdapter


class AdapterRegistry:
    def __init__(self, adapters: Iterable[ExecutionAdapter] = ()) -> None:
        self._adapters: dict[str, ExecutionAdapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: ExecutionAdapter) -> None:
        name = adapter.name.strip()
        if not name:
            raise AdapterRegistryError("adapter name must not be empty")
        if name in self._adapters:
            raise AdapterRegistryError(f"duplicate adapter: {name}")
        if not adapter.operations or any(not item.strip() for item in adapter.operations):
            raise AdapterRegistryError(f"adapter {name} must declare valid operations")
        self._adapters[name] = adapter

    def resolve(self, name: str, operation: str) -> ExecutionAdapter:
        adapter = self._adapters.get(name)
        if adapter is None:
            raise AdapterRegistryError(f"unknown adapter: {name}")
        if operation not in adapter.operations:
            raise AdapterRegistryError(f"adapter {name} does not support operation {operation}")
        return adapter

    def names(self) -> tuple[str, ...]:
        return tuple(sorted(self._adapters))
