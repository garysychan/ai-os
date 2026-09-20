"""Workflow pack execution remains inside Controller authority."""

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
from ai_os.controller import ControllerEngine, ControllerEventType
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
DEPENDENCIES = {"TASK-0015": TaskStatus.DONE}
CAPABILITIES = {
    AgentRole.PLANNER: Capability.PLAN,
    AgentRole.RESEARCHER: Capability.RESEARCH,
    AgentRole.REVIEWER: Capability.REVIEW,
}


class RecordingAgent(Agent):
    def __init__(
        self, role: AgentRole, calls: list[Capability], *, emit_outputs: bool = True
    ) -> None:
        policy = PermissionPolicy()
        self._descriptor = AgentDescriptor(
            role,
            frozenset({CAPABILITIES[role]}),
            policy.permissions_for(role),
            frozenset({TaskStatus.IN_PROGRESS, TaskStatus.REVIEW}),
            "recording pack Agent",
        )
        self.calls = calls
        self.emit_outputs = emit_outputs
        self.reviews = deque([ReviewResult.APPROVE])

    @property
    def descriptor(self) -> AgentDescriptor:
        return self._descriptor

    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        self.calls.append(request.capability)
        review = self.reviews.popleft() if request.capability is Capability.REVIEW else None
        stage = request.evidence[0].removeprefix("workflow-stage:")
        section_by_stage = {
            "research": "facts",
            "valuation": "inference",
            "risk": "assumptions",
        }
        section = section_by_stage.get(stage) if self.emit_outputs else None
        return ExecutionResult(
            request.task.task_id,
            self.descriptor.role,
            request.capability,
            ExecutionStatus.SUCCESS,
            request.capability.value,
            Handoff(
                request.task.task_id,
                request.task.status,
                request.objective,
                (request.capability.value,),
                (),
                (),
                (),
                (),
                "Controller",
                (request.capability.value,),
            ),
            review_result=review,
            output_sections=((section, f"verified {section}"),) if section else (),
        )


def _task(agents: tuple[str, ...] = ("Planner", "Researcher", "Reviewer")) -> Task:
    return Task(
        "TASK-0016",
        "Workflow Definition Packs",
        Priority.P1,
        TaskStatus.IN_PROGRESS,
        agents,
        tuple(DEPENDENCIES),
        (AcceptanceCriterion("pack works", completed=True, evidence=("accepted",)),),
    )


def _engine(
    *, emit_outputs: bool = True
) -> tuple[WorkflowEngine, list[Capability], InMemoryWorkflowStore]:
    calls: list[Capability] = []
    agents = tuple(RecordingAgent(role, calls, emit_outputs=emit_outputs) for role in CAPABILITIES)
    controller = ControllerEngine(AgentRuntime(AgentRouter(AgentRegistry(agents))))
    store = InMemoryWorkflowStore()
    return WorkflowEngine(WorkflowRegistry(core_workflows()), controller, store=store), calls, store


def test_investment_executes_exact_declared_plan_through_controller() -> None:
    engine, calls, _ = _engine()
    result = engine.run(
        _task(),
        "investment",
        "1.0.0",
        "analyze governed investment evidence",
        dependency_states=DEPENDENCIES,
        clock=lambda: NOW,
    )
    definition = engine.registry.resolve("investment", "1.0.0")
    assert calls == [stage.capability for stage in definition.stages]
    assert result.task.status is TaskStatus.DONE
    assert result.session.status is WorkflowStatus.COMPLETED
    assert result.required_output_sections == ("facts", "inference", "assumptions")
    assert dict(result.output_sections) == {
        "facts": "verified facts",
        "inference": "verified inference",
        "assumptions": "verified assumptions",
    }
    assert sum(
        event.event_type is ControllerEventType.AGENT_DISPATCHED
        for event in result.controller_session.events
    ) == len(definition.stages)


def test_pack_assignment_and_pre_dispatch_cancellation_fail_closed() -> None:
    engine, _, store = _engine()
    with pytest.raises(WorkflowPolicyError, match="Researcher is not assigned"):
        engine.start(
            _task(("Planner", "Reviewer")),
            "trace",
            "1.0.0",
            "missing assignment",
            dependency_states=DEPENDENCIES,
            started_at=NOW,
        )
    with pytest.raises(WorkflowPolicyError, match="cancelled"):
        engine.run(
            _task(),
            "trace",
            "1.0.0",
            "cancel before dispatch",
            dependency_states=DEPENDENCIES,
            clock=lambda: NOW,
            cancelled=lambda: True,
        )
    session_id = f"workflow:TASK-0016:trace:1.0.0:{int(NOW.timestamp() * 1_000_000)}"
    assert store.get(session_id).status is WorkflowStatus.CANCELLED


def test_checkpoint_binds_exact_stage_plan_and_policy_budget() -> None:
    engine, _, store = _engine()
    session = engine.start(
        _task(),
        "trace",
        "1.0.0",
        "checkpoint",
        dependency_states=DEPENDENCIES,
        started_at=NOW,
    )
    store.save(replace(session, status=WorkflowStatus.RUNNING))
    definition = engine.registry.resolve("trace", "1.0.0")
    changed_plan = replace(
        definition,
        stages=(replace(definition.stages[0], name="scope"), *definition.stages[1:]),
    )
    with pytest.raises(WorkflowValidationError, match="canonical stage order"):
        WorkflowRegistry((changed_plan,))

    changed_contract = replace(
        definition,
        required_output_sections=(*definition.required_output_sections, "limitations"),
    )
    changed_engine = WorkflowEngine(
        WorkflowRegistry((changed_contract,)), engine.controller, store=store
    )
    with pytest.raises(WorkflowValidationError, match="fingerprint"):
        changed_engine.validate_resume(session.session_id)

    budget_engine = WorkflowEngine(
        WorkflowRegistry((replace(definition, max_steps=5),)), engine.controller, store=store
    )
    with pytest.raises(WorkflowValidationError, match="step budget"):
        budget_engine.validate_resume(session.session_id)


def test_missing_structured_output_fails_before_reviewer_dispatch() -> None:
    engine, calls, _ = _engine(emit_outputs=False)
    result = engine.run(
        _task(),
        "investment",
        "1.0.0",
        "reject missing output sections",
        dependency_states=DEPENDENCIES,
        clock=lambda: NOW,
    )
    assert result.session.status is WorkflowStatus.ESCALATED
    assert calls == [Capability.PLAN, Capability.RESEARCH, Capability.RESEARCH, Capability.RESEARCH]
    assert "missing" in result.controller_session.events[-1].reason


def test_deadline_is_rechecked_after_review_transition_before_dispatch() -> None:
    engine, calls, store = _engine()
    deadline = NOW + timedelta(seconds=1)
    timestamps = iter((*([NOW] * 11), deadline))
    with pytest.raises(WorkflowPolicyError, match="deadline expired"):
        engine.run(
            _task(),
            "investment",
            "1.0.0",
            "expire immediately before Reviewer dispatch",
            dependency_states=DEPENDENCIES,
            clock=lambda: next(timestamps, deadline),
            deadline=deadline,
        )
    assert calls == [Capability.PLAN, Capability.RESEARCH, Capability.RESEARCH, Capability.RESEARCH]
    session_id = f"workflow:TASK-0016:investment:1.0.0:{int(NOW.timestamp() * 1_000_000)}"
    assert store.get(session_id).status is WorkflowStatus.ESCALATED
