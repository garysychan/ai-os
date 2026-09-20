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
    assert result.summary == "[REDACTED]"
    assert result.correlation[-1] == ("api_key", "[REDACTED]")
    assert result.evidence == ("[REDACTED]",)
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
        {"event_id": "event\n1"},
        {"trace_id": "trace\x001"},
        {"task_id": "not-a-task"},
    ],
)
def test_invalid_events_fail_closed(changed: dict[str, object]) -> None:
    with pytest.raises(ObservabilityValidationError):
        sanitize_event(replace(event(), **changed))


def test_opaque_bearer_and_provider_payload_are_redacted_entirely() -> None:
    result = sanitize_event(
        replace(
            event(),
            summary="Authorization: Bearer supersecret",
            evidence=('provider_payload={"token": "raw-secret", "prompt": "private"}',),
        )
    )
    assert result.summary == "[REDACTED]"
    assert result.evidence == ("[REDACTED]",)
