from __future__ import annotations

from datetime import UTC, datetime

import pytest

from ai_os.observability import (
    ObservabilityValidationError,
    RuntimeEventType,
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
    assert result.correlation == (("stage", "CREATED"),)


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
