from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_os.agents import AgentRole
from ai_os.controller import ControllerEventType, ControllerOutcome, ControllerStage, TraceEvent
from ai_os.execution import ExecutionEvent, ExecutionEventType, ExecutionOutcome
from ai_os.observability import (
    ObservabilityValidationError,
    RuntimeEventType,
    from_controller,
    from_execution,
    from_workflow,
)
from ai_os.workflows import WorkflowEvent


def test_workflow_evidence_is_normalized_with_explicit_correlation() -> None:
    result = from_workflow(
        WorkflowEvent(
            sequence=1,
            session_id="workflow-1",
            task_id="TASK-0017",
            event_type="WORKFLOW_STARTED",
            stage="CREATED",
            timestamp=datetime(2026, 9, 20, tzinfo=UTC),
            summary="accepted",
        ),
        trace_id="trace-1",
    )
    assert result.event_type is RuntimeEventType.ACCEPTED
    assert result.trace_id == "trace-1"
    assert result.workflow_session_id == "workflow-1"
    assert result.sequence == 0
    assert result.correlation == (("stage", "CREATED"), ("source_sequence", "1"))


def test_unknown_workflow_event_type_fails_closed() -> None:
    with pytest.raises(ObservabilityValidationError):
        from_workflow(
            WorkflowEvent(
                1,
                "workflow-1",
                "TASK-0017",
                "UNTRUSTED_EVENT",
                "CREATED",
                datetime(2026, 9, 20, tzinfo=UTC),
                "unknown",
            )
        )


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        (ControllerOutcome.COMPLETED, RuntimeEventType.COMPLETED),
        (ControllerOutcome.FAILED, RuntimeEventType.FAILED),
        (ControllerOutcome.CANCELLED, RuntimeEventType.CANCELLED),
        (ControllerOutcome.BLOCKED, RuntimeEventType.DENIED),
    ],
)
def test_controller_terminal_outcomes_are_not_reported_as_success(
    outcome: ControllerOutcome, expected: RuntimeEventType
) -> None:
    source = TraceEvent(
        1,
        "session-1",
        "TASK-0017",
        ControllerEventType.SESSION_TERMINATED,
        ControllerStage.TERMINAL,
        AgentRole.CONTROLLER,
        datetime(2026, 9, 20, tzinfo=UTC),
        "terminal",
    )
    assert from_controller(source, outcome=outcome).event_type is expected


def test_execution_timeout_is_explicit() -> None:
    source = ExecutionEvent(
        1,
        "execution-1",
        "TASK-0017",
        ExecutionEventType.SESSION_FINISHED,
        datetime(2026, 9, 20, tzinfo=UTC),
        "deadline exhausted",
    )
    result = from_execution(source, outcome=ExecutionOutcome.ESCALATED, timed_out=True)
    assert result.event_type is RuntimeEventType.TIMED_OUT
