"""Tool Registry registration and resolution tests."""

from dataclasses import replace
from pathlib import Path

import pytest

from ai_os.adapters import AdapterRegistry, ReadOnlyFileAdapter, SideEffect
from ai_os.tools import ToolRegistry, ToolRegistryError, core_tools


def registry(root: Path) -> ToolRegistry:
    adapters = AdapterRegistry((ReadOnlyFileAdapter((root,)),))
    return ToolRegistry(adapters, core_tools())


def test_registry_is_versioned_explicit_and_default_deny(tmp_path: Path) -> None:
    tools = registry(tmp_path)
    assert tools.resolve("file", "1").description
    assert tools.resolve_operation("file", "1", "read_text").adapter == "file-read"
    with pytest.raises(ToolRegistryError, match="unknown Tool"):
        tools.resolve("shell", "1")
    with pytest.raises(ToolRegistryError, match="unsupported Tool operation"):
        tools.resolve_operation("file", "1", "write_text")
    with pytest.raises(ToolRegistryError, match="duplicate"):
        tools.register(core_tools()[0])


def test_registry_rejects_unresolved_or_mismatched_adapter_bindings(tmp_path: Path) -> None:
    adapters = AdapterRegistry((ReadOnlyFileAdapter((tmp_path,)),))
    metadata = core_tools()[0]
    operation = metadata.operations[0]
    with pytest.raises(ToolRegistryError, match="invalid Adapter binding"):
        ToolRegistry(
            adapters,
            (replace(metadata, operations=(replace(operation, adapter="unknown"),)),),
        )
    with pytest.raises(ToolRegistryError, match="side effect"):
        ToolRegistry(
            adapters,
            (
                replace(
                    metadata,
                    operations=(replace(operation, side_effect=SideEffect.NONE),),
                ),
            ),
        )
