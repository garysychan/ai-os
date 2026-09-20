from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime

import pytest

from ai_os.observability import (
    ObservabilityValidationError,
    RuntimeEvent,
    RuntimeEventSource,
    RuntimeEventType,
    sanitize_event,
)


def event() -> RuntimeEvent:
    return RuntimeEvent(
        event_id="event-1",
        sequence=1,
        timestamp=datetime(2026, 9, 20, tzinfo=UTC),
        event_type=RuntimeEventType.STARTED,
        source=RuntimeEventSource.EXECUTION,
        task_id="TASK-0017",
        trace_id="trace-1",
        summary="started token=do-not-store",
        correlation=(("execution_id", "execution-1"), ("api_key", "unsafe")),
        evidence=("Authorization: Bearer-secret",),
    )


def test_sanitize_event_redacts_sensitive_values_before_persistence() -> None:
    result = sanitize_event(event())
    assert result.summary == "started token=[REDACTED]"
    assert result.correlation[-1] == ("api_key", "[REDACTED]")
    assert result.evidence == ("Authorization:[REDACTED]",)
    assert "do-not-store" not in repr(result)


@pytest.mark.parametrize(
    "changed",
    [
        {"schema_version": 2},
        {"sequence": 0},
        {"event_id": " "},
        {"trace_id": ""},
        {"summary": ""},
        {"timestamp": datetime(2026, 9, 20)},
        {"correlation": (("same", "1"), ("same", "2"))},
    ],
)
def test_invalid_events_fail_closed(changed: dict[str, object]) -> None:
    with pytest.raises(ObservabilityValidationError):
        sanitize_event(replace(event(), **changed))
