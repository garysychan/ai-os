"""Versioned, explicit and default-deny Tool Registry."""

from ai_os.adapters import AdapterRegistry, AdapterRegistryError

from .errors import ToolRegistryError
from .models import ToolMetadata, ToolOperation
from .validation import validate_metadata


class ToolRegistry:
    """Register Tools only when every operation resolves to a known Adapter."""

    def __init__(
        self,
        adapter_registry: AdapterRegistry,
        tools: tuple[ToolMetadata, ...] = (),
    ) -> None:
        self.adapter_registry = adapter_registry
        self._tools: dict[tuple[str, str], ToolMetadata] = {}
        for tool in tools:
            self.register(tool)

    def register(self, metadata: ToolMetadata) -> None:
        validate_metadata(metadata)
        key = (metadata.name, metadata.version)
        if key in self._tools:
            raise ToolRegistryError(
                f"duplicate Tool registration: {metadata.name}@{metadata.version}"
            )
        for operation in metadata.operations:
            try:
                adapter = self.adapter_registry.resolve(
                    operation.adapter,
                    operation.adapter_version,
                    operation.adapter_operation,
                )
            except AdapterRegistryError as error:
                raise ToolRegistryError(
                    f"Tool operation {metadata.name}.{operation.name} has invalid "
                    f"Adapter binding: {error}"
                ) from error
            adapter_metadata = adapter.metadata
            if operation.side_effect is not adapter_metadata.side_effect:
                raise ToolRegistryError("Tool side effect must match its Adapter")
            if operation.risk is not adapter_metadata.risk:
                raise ToolRegistryError("Tool risk must match its Adapter")
            adapter_idempotent = (
                operation.adapter_operation in adapter_metadata.idempotent_operations
            )
            if operation.idempotent is not adapter_idempotent:
                raise ToolRegistryError("Tool idempotency must match its Adapter")
        self._tools[key] = metadata

    def resolve(self, name: str, version: str) -> ToolMetadata:
        metadata = self._tools.get((name, version))
        if metadata is None:
            raise ToolRegistryError(f"unknown Tool: {name}@{version}")
        return metadata

    def resolve_operation(self, name: str, version: str, operation: str) -> ToolOperation:
        metadata = self.resolve(name, version)
        resolved = next((item for item in metadata.operations if item.name == operation), None)
        if resolved is None:
            raise ToolRegistryError(f"unsupported Tool operation: {name}.{operation}")
        return resolved

    def list_metadata(self) -> tuple[ToolMetadata, ...]:
        return tuple(self._tools[key] for key in sorted(self._tools))
