"""Explicit default-deny Adapter Registry."""

from .errors import AdapterRegistryError
from .protocol import Adapter


class AdapterRegistry:
    def __init__(self, adapters: tuple[Adapter, ...] = ()) -> None:
        self._adapters: dict[tuple[str, str], Adapter] = {}
        for adapter in adapters:
            self.register(adapter)

    def register(self, adapter: Adapter) -> None:
        metadata = adapter.metadata
        if not metadata.name.strip() or not metadata.version.strip():
            raise AdapterRegistryError("adapter name and version must not be empty")
        if not metadata.operations:
            raise AdapterRegistryError("adapter must declare at least one operation")
        key = (metadata.name, metadata.version)
        if key in self._adapters:
            raise AdapterRegistryError(
                f"duplicate adapter registration: {metadata.name}@{metadata.version}"
            )
        self._adapters[key] = adapter

    def resolve(self, name: str, version: str, operation: str) -> Adapter:
        adapter = self._adapters.get((name, version))
        if adapter is None:
            raise AdapterRegistryError(f"unknown adapter: {name}@{version}")
        if operation not in adapter.metadata.operations:
            raise AdapterRegistryError(f"unsupported operation: {name}.{operation}")
        return adapter

    def list_metadata(self) -> tuple[object, ...]:
        return tuple(
            adapter.metadata
            for _, adapter in sorted(self._adapters.items(), key=lambda item: item[0])
        )
