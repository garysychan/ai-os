"""Deterministic, validated JSON codecs for persistent runtime records."""

from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime
from enum import Enum
from typing import Any, TypeVar, cast

from ai_os.adapters import AdapterAuditEvent, AdapterStatus, redact_text
from ai_os.agents import (
    AgentRole,
    Capability,
    ExecutionStatus,
    Handoff,
    Permission,
)
from ai_os.agents import (
    ExecutionResult as AgentExecutionResult,
)
from ai_os.controller import (
    ControllerEventType,
    ControllerOutcome,
    ControllerSession,
    ControllerStage,
    TraceEvent,
)
from ai_os.execution import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionOutcome,
    ExecutionPlan,
    ExecutionSession,
    ExecutionStep,
    StepResult,
    StepStatus,
)
from ai_os.tasks import ReviewResult, TaskStatus
from ai_os.workflow import TransitionEvent

from .errors import PersistenceIntegrityError

_CODEC_VERSION = 1
_T = TypeVar("_T")


def _json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise PersistenceIntegrityError("timestamps must be timezone-aware")
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_json_value(item) for item in value]
    if isinstance(value, (str, int, float, bool)) or value is None:
        return redact_text(value) if isinstance(value, str) else value
    raise PersistenceIntegrityError(f"unsupported persistence value: {type(value).__name__}")


def _dump(kind: str, value: object) -> str:
    return json.dumps(
        {"codec_version": _CODEC_VERSION, "kind": kind, "data": _json_value(value)},
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )


def _load(payload: str, kind: str) -> dict[str, Any]:
    try:
        envelope = json.loads(payload)
    except (json.JSONDecodeError, TypeError) as error:
        raise PersistenceIntegrityError("stored payload is not valid JSON") from error
    if not isinstance(envelope, dict):
        raise PersistenceIntegrityError("stored payload envelope must be an object")
    if envelope.get("codec_version") != _CODEC_VERSION:
        raise PersistenceIntegrityError("unknown persistence codec version")
    if envelope.get("kind") != kind or not isinstance(envelope.get("data"), dict):
        raise PersistenceIntegrityError(f"stored payload is not a {kind}")
    return cast(dict[str, Any], envelope["data"])


def _enum(enum_type: type[_T], value: Any, field: str) -> _T:
    try:
        return enum_type(value)  # type: ignore[call-arg]
    except (TypeError, ValueError) as error:
        raise PersistenceIntegrityError(f"invalid {field}") from error


def _dt(value: Any, field: str) -> datetime:
    if not isinstance(value, str):
        raise PersistenceIntegrityError(f"invalid {field}")
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as error:
        raise PersistenceIntegrityError(f"invalid {field}") from error
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise PersistenceIntegrityError(f"{field} must be timezone-aware")
    return parsed


def _tuple_strings(value: Any, field: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise PersistenceIntegrityError(f"invalid {field}")
    return tuple(value)


def _pairs(value: Any, field: str) -> tuple[tuple[str, str], ...]:
    if not isinstance(value, list):
        raise PersistenceIntegrityError(f"invalid {field}")
    pairs: list[tuple[str, str]] = []
    for item in value:
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(part, str) for part in item)
        ):
            raise PersistenceIntegrityError(f"invalid {field}")
        pairs.append((item[0], item[1]))
    return tuple(pairs)


def dump_controller_session(session: ControllerSession) -> str:
    return _dump("controller_session", session)


def load_controller_session(payload: str) -> ControllerSession:
    data = _load(payload, "controller_session")
    try:
        events = tuple(
            TraceEvent(
                sequence=item["sequence"],
                session_id=item["session_id"],
                task_id=item["task_id"],
                event_type=_enum(ControllerEventType, item["event_type"], "event_type"),
                stage=_enum(ControllerStage, item["stage"], "stage"),
                actor=_enum(AgentRole, item["actor"], "actor"),
                timestamp=_dt(item["timestamp"], "event timestamp"),
                reason=item["reason"],
                evidence=_tuple_strings(item["evidence"], "event evidence"),
                correlation=_pairs(item["correlation"], "event correlation"),
            )
            for item in data["events"]
        )
        results = tuple(_load_agent_result(item) for item in data["results"])
        transitions = tuple(
            TransitionEvent(
                task_id=item["task_id"],
                source=_enum(TaskStatus, item["source"], "transition source"),
                target=_enum(TaskStatus, item["target"], "transition target"),
                actor=item["actor"],
                reason=item["reason"],
                timestamp=_dt(item["timestamp"], "transition timestamp"),
                evidence=_tuple_strings(item["evidence"], "transition evidence"),
            )
            for item in data["transitions"]
        )
        outcome = data["outcome"]
        return ControllerSession(
            session_id=data["session_id"],
            task_id=data["task_id"],
            objective=data["objective"],
            stage=_enum(ControllerStage, data["stage"], "stage"),
            task_status=_enum(TaskStatus, data["task_status"], "task_status"),
            started_at=_dt(data["started_at"], "started_at"),
            updated_at=_dt(data["updated_at"], "updated_at"),
            max_fix_attempts=data["max_fix_attempts"],
            fix_attempts=data["fix_attempts"],
            approval_evidence=_tuple_strings(data["approval_evidence"], "approval evidence"),
            events=events,
            results=results,
            transitions=transitions,
            blocking_findings=_tuple_strings(data["blocking_findings"], "blocking findings"),
            outcome=None if outcome is None else _enum(ControllerOutcome, outcome, "outcome"),
        )
    except (KeyError, TypeError) as error:
        raise PersistenceIntegrityError("invalid controller session payload") from error


def _load_agent_result(item: dict[str, Any]) -> AgentExecutionResult:
    handoff = item["handoff"]
    review = item["review_result"]
    return AgentExecutionResult(
        task_id=item["task_id"],
        role=_enum(AgentRole, item["role"], "result role"),
        capability=_enum(Capability, item["capability"], "result capability"),
        status=_enum(ExecutionStatus, item["status"], "result status"),
        summary=item["summary"],
        handoff=Handoff(
            task_id=handoff["task_id"],
            state=_enum(TaskStatus, handoff["state"], "handoff state"),
            objective=handoff["objective"],
            completed=_tuple_strings(handoff["completed"], "handoff completed"),
            artifacts=_tuple_strings(handoff["artifacts"], "handoff artifacts"),
            tests=_tuple_strings(handoff["tests"], "handoff tests"),
            risks=_tuple_strings(handoff["risks"], "handoff risks"),
            remaining=_tuple_strings(handoff["remaining"], "handoff remaining"),
            next_action=handoff["next_action"],
            evidence=_tuple_strings(handoff["evidence"], "handoff evidence"),
        ),
        review_result=None if review is None else _enum(ReviewResult, review, "review result"),
        findings=_tuple_strings(item["findings"], "result findings"),
        errors=_tuple_strings(item["errors"], "result errors"),
    )


def dump_execution_plan(plan: ExecutionPlan) -> str:
    return _dump("execution_plan", plan)


def load_execution_plan(payload: str) -> ExecutionPlan:
    data = _load(payload, "execution_plan")
    try:
        return ExecutionPlan(
            plan_id=data["plan_id"],
            task_id=data["task_id"],
            steps=tuple(
                ExecutionStep(
                    step_id=item["step_id"],
                    adapter=item["adapter"],
                    operation=item["operation"],
                    agent_role=_enum(AgentRole, item["agent_role"], "agent_role"),
                    capability=_enum(Capability, item["capability"], "capability"),
                    required_permission=_enum(
                        Permission, item["required_permission"], "required_permission"
                    ),
                    inputs=_pairs(item["inputs"], "step inputs"),
                    idempotent=item["idempotent"],
                    max_retries=item["max_retries"],
                )
                for item in data["steps"]
            ),
            max_steps=data["max_steps"],
        )
    except (KeyError, TypeError) as error:
        raise PersistenceIntegrityError("invalid execution plan payload") from error


def dump_execution_session(session: ExecutionSession) -> str:
    return _dump("execution_session", session)


def load_execution_session(payload: str) -> ExecutionSession:
    data = _load(payload, "execution_session")
    try:
        events = tuple(
            ExecutionEvent(
                sequence=item["sequence"],
                execution_id=item["execution_id"],
                task_id=item["task_id"],
                event_type=_enum(ExecutionEventType, item["event_type"], "event_type"),
                timestamp=_dt(item["timestamp"], "event timestamp"),
                reason=item["reason"],
                step_id=item["step_id"],
                attempt=item["attempt"],
                evidence=_tuple_strings(item["evidence"], "event evidence"),
            )
            for item in data["events"]
        )
        results = tuple(
            StepResult(
                step_id=item["step_id"],
                attempt=item["attempt"],
                status=_enum(StepStatus, item["status"], "step status"),
                summary=item["summary"],
                outputs=_pairs(item["outputs"], "step outputs"),
                evidence=_tuple_strings(item["evidence"], "step evidence"),
                errors=_tuple_strings(item["errors"], "step errors"),
            )
            for item in data["results"]
        )
        outcome = data["outcome"]
        return ExecutionSession(
            execution_id=data["execution_id"],
            plan_id=data["plan_id"],
            task_id=data["task_id"],
            controller_session_id=data["controller_session_id"],
            started_at=_dt(data["started_at"], "started_at"),
            updated_at=_dt(data["updated_at"], "updated_at"),
            events=events,
            results=results,
            outcome=None if outcome is None else _enum(ExecutionOutcome, outcome, "outcome"),
            blocking_findings=_tuple_strings(data["blocking_findings"], "blocking findings"),
        )
    except (KeyError, TypeError) as error:
        raise PersistenceIntegrityError("invalid execution session payload") from error


def dump_adapter_audit(event: AdapterAuditEvent) -> str:
    return _dump("adapter_audit", event)


def load_adapter_audit(payload: str) -> AdapterAuditEvent:
    data = _load(payload, "adapter_audit")
    try:
        return AdapterAuditEvent(
            sequence=data["sequence"],
            invocation_id=data["invocation_id"],
            task_id=data["task_id"],
            adapter=data["adapter"],
            operation=data["operation"],
            timestamp=_dt(data["timestamp"], "timestamp"),
            status=_enum(AdapterStatus, data["status"], "status"),
            evidence=_tuple_strings(data["evidence"], "evidence"),
        )
    except (KeyError, TypeError) as error:
        raise PersistenceIntegrityError("invalid adapter audit payload") from error
