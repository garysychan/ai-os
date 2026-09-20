"""Workflow Engine integration over the existing Controller lifecycle."""

from collections import deque
from dataclasses import replace
from datetime import UTC, datetime, timedelta

import pytest

from ai_os.agents import (
    Agent,
    AgentDescriptor,
    AgentRegistry,
    AgentRole,
    AgentRouter,
    AgentRuntime,
    Capability,
    ExecutionRequest,
    ExecutionResult,
    ExecutionStatus,
    Handoff,
    PermissionPolicy,
)
from ai_os.controller import ControllerEngine
from ai_os.tasks import AcceptanceCriterion, Priority, ReviewResult, Task, TaskStatus
from ai_os.workflows import (
    InMemoryWorkflowStore,
    WorkflowEngine,
    WorkflowPolicyError,
    WorkflowRegistry,
    WorkflowStatus,
    WorkflowValidationError,
    core_workflows,
)

NOW = datetime(2026, 9, 18, tzinfo=UTC)
DEPENDENCIES = {"TASK-0014": TaskStatus.DONE}
CAPABILITIES = {
    AgentRole.DEVELOPER: Capability.IMPLEMENT,
    AgentRole.TESTER: Capability.TEST,
    AgentRole.REVIEWER: Capability.REVIEW,
    AgentRole.FIXER: Capability.FIX,
}


class ScriptedAgent(Agent):
    def __init__(
        self,
        role: AgentRole,
        statuses: tuple[ExecutionStatus, ...],
        reviews: tuple[ReviewResult | None, ...] = (),
    ) -> None:
        policy = PermissionPolicy()
        self._descriptor = AgentDescriptor(
            role,
            frozenset({CAPABILITIES[role]}),
            policy.permissions_for(role),
            frozenset({TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}),
            "scripted Workflow test Agent",
        )
        self.statuses = deque(statuses)
        self.reviews = deque(reviews)

    @property
    def descriptor(self) -> AgentDescriptor:
        return self._descriptor

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        status = self.statuses.popleft()
        review = self.reviews.popleft() if self.reviews else None
        summary = f"{self.descriptor.role.value}: {status.value}"
        return ExecutionResult(
            request.task.task_id,
            self.descriptor.role,
            request.capability,
            status,
            summary,
            Handoff(
                request.task.task_id,
                request.task.status,
                request.objective,
                (summary,),
                (),
                (summary,) if request.capability is Capability.TEST else (),
                (),
                (),
                "Controller",
                (summary,),
            ),
            review_result=review,
            findings=(summary,) if status is not ExecutionStatus.SUCCESS else (),
        )


def task() -> Task:
    return Task(
        "TASK-0015",
        "Workflow Engine",
        Priority.P1,
        TaskStatus.IN_PROGRESS,
        ("Developer", "Tester", "Reviewer", "Fixer"),
        tuple(DEPENDENCIES),
        (AcceptanceCriterion("workflow works", completed=True, evidence=("accepted",)),),
    )


def engine(
    tests: tuple[ExecutionStatus, ...] = (ExecutionStatus.SUCCESS,),
    reviews: tuple[ReviewResult, ...] = (ReviewResult.APPROVE,),
    fixes: tuple[ExecutionStatus, ...] = (ExecutionStatus.SUCCESS,),
    max_steps: int | None = None,
) -> tuple[WorkflowEngine, InMemoryWorkflowStore]:
    agents = (
        ScriptedAgent(AgentRole.DEVELOPER, (ExecutionStatus.SUCCESS,)),
        ScriptedAgent(AgentRole.TESTER, tests),
        ScriptedAgent(
            AgentRole.REVIEWER,
            tuple(ExecutionStatus.SUCCESS for _ in reviews),
            reviews,
        ),
        ScriptedAgent(AgentRole.FIXER, fixes),
    )
    store = InMemoryWorkflowStore()
    controller = ControllerEngine(AgentRuntime(AgentRouter(AgentRegistry(agents))))
    definitions = core_workflows()
    if max_steps is not None:
        definitions = (replace(definitions[0], max_steps=max_steps),)
    return WorkflowEngine(WorkflowRegistry(definitions), controller, store=store), store


def test_pre_execution_workflow_denial_is_emitted() -> None:
    workflow, _ = engine()
    denied: list[tuple[str, str]] = []
    workflow.denial_sink = lambda task_id, _workflow, _timestamp, reason: denied.append(
        (task_id, reason)
    )
    with pytest.raises(WorkflowPolicyError):
        workflow.start(
            replace(task(), status=TaskStatus.TODO),
            "coding",
            "1",
            "not authorized",
            dependency_states=DEPENDENCIES,
            started_at=NOW,
        )
    assert denied == [("TASK-0015", "WorkflowPolicyError")]


def test_coding_workflow_completes_through_controller_and_state_machine() -> None:
    runtime, store = engine()
    result = runtime.run(
        task(),
        "coding",
        "1",
        "implement Workflow Engine",
        dependency_states=DEPENDENCIES,
        clock=lambda: NOW,
        deadline=NOW + timedelta(minutes=1),
        approval_evidence=("APPROVE CR-2026-012",),
    )
    assert result.task.status is TaskStatus.DONE
    assert result.session.status is WorkflowStatus.COMPLETED
    assert result.session.controller_session_id
    assert store.get(result.session.session_id) == result.session
    assert tuple(event.sequence for event in result.session.events) == tuple(
        range(1, len(result.session.events) + 1)
    )


def test_controller_finite_fix_cycle_is_preserved() -> None:
    runtime, _ = engine(
        tests=(ExecutionStatus.FAILED, ExecutionStatus.SUCCESS),
        fixes=(ExecutionStatus.SUCCESS,),
    )
    result = runtime.run(
        task(),
        "coding",
        "1",
        "fix then complete",
        dependency_states=DEPENDENCIES,
        clock=lambda: NOW,
        max_fix_attempts=1,
    )
    assert result.session.status is WorkflowStatus.COMPLETED
    assert result.controller_session.fix_attempts == 1


def test_workflow_step_budget_fails_closed() -> None:
    runtime, store = engine(
        tests=(ExecutionStatus.FAILED, ExecutionStatus.SUCCESS),
        fixes=(ExecutionStatus.SUCCESS,),
        max_steps=4,
    )
    with pytest.raises(WorkflowPolicyError, match="step budget exhausted"):
        runtime.run(
            task(),
            "coding",
            "1",
            "reject excess dispatches",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            max_fix_attempts=1,
        )
    session_id = f"workflow:TASK-0015:coding:1:{int(NOW.timestamp() * 1_000_000)}"
    aborted = store.get(session_id)
    assert aborted.status is WorkflowStatus.ESCALATED
    assert aborted.events[-1].event_type == "WORKFLOW_ABORTED"


def test_pre_dispatch_cancellation_and_deadline_fail_closed() -> None:
    runtime, store = engine()
    with pytest.raises(WorkflowPolicyError, match="cancelled"):
        runtime.run(
            task(),
            "coding",
            "1",
            "cancelled",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            cancelled=lambda: True,
        )
    session_id = f"workflow:TASK-0015:coding:1:{int(NOW.timestamp() * 1_000_000)}"
    assert store.get(session_id).status is WorkflowStatus.CANCELLED
    runtime, store = engine()
    deadline = NOW + timedelta(seconds=1)
    timestamps = iter((NOW, deadline))
    with pytest.raises(WorkflowPolicyError, match="expired"):
        runtime.run(
            task(),
            "coding",
            "1",
            "expired",
            dependency_states=DEPENDENCIES,
            clock=lambda: next(timestamps, deadline),
            deadline=deadline,
        )
    assert store.get(session_id).status is WorkflowStatus.ESCALATED


def test_resume_rejects_terminal_version_mismatch_and_corrupt_events() -> None:
    runtime, store = engine()
    created = runtime.start(
        task(),
        "coding",
        "1",
        "checkpoint",
        dependency_states=DEPENDENCIES,
        started_at=NOW,
    )
    running = replace(created, status=WorkflowStatus.RUNNING)
    store.save(running)
    assert runtime.validate_resume(running.session_id) == running

    store.save(replace(running, status=WorkflowStatus.COMPLETED))
    with pytest.raises(WorkflowValidationError, match="terminal"):
        runtime.validate_resume(running.session_id)

    store.save(replace(running, workflow_version="2"))
    with pytest.raises(Exception, match="unknown Workflow"):
        runtime.validate_resume(running.session_id)

    corrupt = replace(running.events[0], sequence=2)
    store.save(replace(running, events=(corrupt,)))
    with pytest.raises(WorkflowValidationError, match="sequence is corrupt"):
        runtime.validate_resume(running.session_id)
