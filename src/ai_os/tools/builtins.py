"""Canonical core Tool declarations."""

from ai_os.adapters import AdapterRisk, SideEffect
from ai_os.agents import Capability, Permission

from .models import ToolMetadata, ToolOperation


def core_tools() -> tuple[ToolMetadata, ...]:
    """Return the minimal built-in Tool catalog without external writes."""
    return (
        ToolMetadata(
            name="file",
            version="1",
            description="Read text from an explicitly approved local root.",
            operations=(
                ToolOperation(
                    name="read_text",
                    capability=Capability.IMPLEMENT,
                    required_permission=Permission.MODIFY_CODE,
                    risk=AdapterRisk.LOW,
                    side_effect=SideEffect.READ_EXTERNAL,
                    idempotent=True,
                    approval_required=False,
                    adapter="file-read",
                    adapter_version="1",
                    adapter_operation="read_text",
                ),
            ),
        ),
    )
