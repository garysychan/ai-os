"""Deterministic Workflow definition and checkpoint validation."""

from ai_os.agents import AgentRole, Capability, Permission
from ai_os.agents.permissions import CAPABILITY_PERMISSION

from .errors import WorkflowValidationError
from .models import (
    TERMINAL_WORKFLOW_STATUSES,
    WorkflowDefinition,
    WorkflowSession,
)

_SUPPORTED_DRIVERS = frozenset({"controller_lifecycle"})
_CONTROLLER_LIFECYCLE = (
    ("implement", AgentRole.DEVELOPER, Capability.IMPLEMENT, Permission.MODIFY_CODE),
    ("test", AgentRole.TESTER, Capability.TEST, Permission.READ_CONTROL),
    ("review", AgentRole.REVIEWER, Capability.REVIEW, Permission.APPROVE_REVIEW),
    ("fix", AgentRole.FIXER, Capability.FIX, Permission.MODIFY_CODE),
)


def validate_definition(definition: WorkflowDefinition) -> None:
    if not definition.name.strip() or not definition.version.strip():
        raise WorkflowValidationError("Workflow name and version must not be empty")
    if not definition.description.strip():
        raise WorkflowValidationError("Workflow description must not be empty")
    if definition.driver not in _SUPPORTED_DRIVERS:
        raise WorkflowValidationError(f"unsupported Workflow driver: {definition.driver}")
    if not definition.stages:
        raise WorkflowValidationError("Workflow must declare at least one stage")
    names = [stage.name for stage in definition.stages]
    if any(not name.strip() for name in names) or len(names) != len(set(names)):
        raise WorkflowValidationError("Workflow stage names must be non-empty and unique")
    if definition.max_steps <= 0 or definition.max_steps < len(definition.stages):
        raise WorkflowValidationError("Workflow step budget must cover every declared stage")
    if definition.max_fix_attempts < 0:
        raise WorkflowValidationError("Workflow fix budget must not be negative")
    for stage in definition.stages:
        canonical = CAPABILITY_PERMISSION[stage.capability]
        if stage.required_permission is not canonical:
            raise WorkflowValidationError(
                f"stage {stage.name} capability {stage.capability.value} requires {canonical.value}"
            )
    declared = tuple(
        (stage.name, stage.agent_role, stage.capability, stage.required_permission)
        for stage in definition.stages
    )
    if definition.driver == "controller_lifecycle" and declared != _CONTROLLER_LIFECYCLE:
        raise WorkflowValidationError(
            "controller_lifecycle requires the canonical implement/test/review/fix stages"
        )


def validate_checkpoint(session: WorkflowSession, definition: WorkflowDefinition) -> None:
    validate_definition(definition)
    if (session.workflow, session.workflow_version) != (
        definition.name,
        definition.version,
    ):
        raise WorkflowValidationError("checkpoint Workflow version does not match definition")
    if session.status in TERMINAL_WORKFLOW_STATUSES:
        raise WorkflowValidationError("terminal Workflow session cannot be resumed")
    if session.max_steps != definition.max_steps:
        raise WorkflowValidationError("checkpoint step budget does not match definition")
    if session.max_fix_attempts < 0 or session.max_fix_attempts > definition.max_fix_attempts:
        raise WorkflowValidationError("checkpoint Fix Cycle budget does not match definition")
    if not session.objective.strip():
        raise WorkflowValidationError("checkpoint objective is empty")
    if session.updated_at < session.started_at:
        raise WorkflowValidationError("checkpoint timestamps are corrupt")
    sequences = tuple(event.sequence for event in session.events)
    if sequences != tuple(range(1, len(sequences) + 1)):
        raise WorkflowValidationError("checkpoint event sequence is corrupt")
    if any(
        event.session_id != session.session_id or event.task_id != session.task_id
        for event in session.events
    ):
        raise WorkflowValidationError("checkpoint event identity is corrupt")
    if any(event.timestamp < session.started_at for event in session.events):
        raise WorkflowValidationError("checkpoint event timestamp is corrupt")
