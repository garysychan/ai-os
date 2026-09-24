"""Application services shared by the governed HTTP boundary."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from importlib.metadata import PackageNotFoundError, version
from typing import Any, cast

from ai_os.agents import AgentRole, Permission, PermissionPolicy, canonical_agents
from ai_os.agents.permissions import CAPABILITY_PERMISSION
from ai_os.execution import ExecutionPlan, ExecutionStep
from ai_os.governance import load_control_plane, run_consistency_checks
from ai_os.monitoring import MonitoringQueryContext, MonitoringService
from ai_os.observability import AuditQueryContext, ObservabilityService, RuntimeEventFilter
from ai_os.persistence import ExecutionRepository
from ai_os.workflows import (
    WorkflowDefinition,
    WorkflowRegistry,
    WorkflowStage,
    core_workflows,
    validate_definition,
)

from .config import ApiConfig
from .models import ExecutionPlanInput, WorkflowInput


def _enum_value(value: object) -> object:
    return getattr(value, "value", value)


def _serialize(value: object) -> object:
    if hasattr(value, "__dataclass_fields__"):
        return {key: _serialize(item) for key, item in asdict(cast(Any, value)).items()}
    if isinstance(value, dict):
        return {str(key): _serialize(item) for key, item in value.items()}
    if isinstance(value, (tuple, list, set, frozenset)):
        return [_serialize(item) for item in value]
    if hasattr(value, "isoformat"):
        return cast(Any, value).isoformat()
    return _enum_value(value)


@dataclass(frozen=True)
class RuntimeApiServices:
    config: ApiConfig
    execution_repository: ExecutionRepository | None = None
    observability: ObservabilityService | None = None
    monitoring: MonitoringService | None = None
    workflow_registry_service: WorkflowRegistry | None = None

    def version(self) -> dict[str, object]:
        try:
            package_version = version("ai-os")
        except PackageNotFoundError:
            package_version = "0.1.0a0"
        return {"api_version": "v1", "ai_os_version": package_version}

    def capabilities(self) -> dict[str, object]:
        return {
            "operations": ["read", "validate", "dry-run"],
            "mutation": False,
            "execution_dispatch": False,
            "max_page_size": self.config.max_page_size,
            "max_dry_run_steps": self.config.max_dry_run_steps,
        }

    def control_plane(self) -> object:
        control = load_control_plane(self.config.root)
        return {
            "root": ".",
            "documents": sorted(control.documents),
            "agents": sorted(control.agents),
            "task_count": len(control.tasks),
            "warnings": list(control.warnings),
        }

    def check_control_plane(self) -> object:
        report = run_consistency_checks(load_control_plane(self.config.root))
        return _serialize(report)

    def tasks(self, *, offset: int, limit: int) -> tuple[list[object], int]:
        tasks = sorted(
            load_control_plane(self.config.root).tasks.values(),
            key=lambda item: item.task_id,
        )
        return [self._task(item) for item in tasks[offset : offset + limit]], len(tasks)

    def task(self, task_id: str) -> object:
        tasks = load_control_plane(self.config.root).tasks
        if task_id not in tasks:
            raise KeyError(task_id)
        return self._task(tasks[task_id])

    def transitions(self) -> object:
        return [
            {"source": source, "target": target}
            for source, target in load_control_plane(self.config.root).workflow.transitions
        ]

    @staticmethod
    def _task(item: object) -> object:
        return _serialize(item)

    def agents(self) -> list[object]:
        return [self._agent(agent.descriptor) for agent in canonical_agents()]

    def agent(self, role: AgentRole) -> object:
        for agent in canonical_agents():
            if agent.descriptor.role is role:
                return self._agent(agent.descriptor)
        raise KeyError(role.value)

    @staticmethod
    def _agent(descriptor: object) -> object:
        return _serialize(descriptor)

    @staticmethod
    def workflow_registry() -> WorkflowRegistry:
        return WorkflowRegistry(core_workflows())

    def workflows(self) -> list[object]:
        registry = self.workflow_registry_service or self.workflow_registry()
        return [_serialize(item) for item in registry.list_definitions()]

    def workflow(self, name: str, workflow_version: str) -> object:
        registry = self.workflow_registry_service or self.workflow_registry()
        return _serialize(registry.resolve(name, workflow_version))

    def validate_workflow(self, payload: WorkflowInput) -> object:
        definition = self._workflow_definition(payload)
        validate_definition(definition)
        return {
            "valid": True,
            "name": definition.name,
            "version": definition.version,
            "stage_count": len(definition.stages),
        }

    def dry_run_workflow(self, payload: WorkflowInput) -> object:
        definition = self._workflow_definition(payload)
        validate_definition(definition)
        if len(definition.stages) > self.config.max_dry_run_steps:
            raise ValueError("workflow exceeds the configured dry-run step bound")
        return {
            "valid": True,
            "dispatched": False,
            "workflow": f"{definition.name}@{definition.version}",
            "stages": [
                {
                    "name": item.name,
                    "agent_role": item.agent_role.value,
                    "capability": item.capability.value,
                    "required_permission": item.required_permission.value,
                }
                for item in definition.stages
            ],
        }

    @staticmethod
    def _workflow_definition(payload: WorkflowInput) -> WorkflowDefinition:
        return WorkflowDefinition(
            name=payload.name,
            version=payload.version,
            description=payload.description,
            driver=payload.driver,
            stages=tuple(
                WorkflowStage(item.name, item.agent_role, item.capability, item.required_permission)
                for item in payload.stages
            ),
            max_steps=payload.max_steps,
            max_fix_attempts=payload.max_fix_attempts,
            approval_required=payload.approval_required,
            required_output_sections=payload.required_output_sections,
        )

    def validate_execution(self, payload: ExecutionPlanInput) -> object:
        plan = self._execution_plan(payload)
        self._validate_execution_plan(plan)
        return {"valid": True, "plan": _serialize(plan)}

    def dry_run_execution(self, payload: ExecutionPlanInput) -> object:
        plan = self._execution_plan(payload)
        self._validate_execution_plan(plan)
        return {"valid": True, "dispatched": False, "plan": _serialize(plan)}

    def _validate_execution_plan(self, plan: ExecutionPlan) -> None:
        if plan.max_steps < len(plan.steps):
            raise ValueError("execution max_steps must cover every declared step")
        if len(plan.steps) > self.config.max_dry_run_steps:
            raise ValueError("execution exceeds the configured dry-run step bound")
        step_ids = [item.step_id for item in plan.steps]
        if len(step_ids) != len(set(step_ids)):
            raise ValueError("execution step identifiers must be unique")
        policy = PermissionPolicy()
        for step in plan.steps:
            if CAPABILITY_PERMISSION[step.capability] is not step.required_permission:
                raise ValueError("execution capability requires its canonical permission")
            if not policy.allows(step.agent_role, step.required_permission):
                raise ValueError("execution step permission is not authorized for its role")

    @staticmethod
    def _execution_plan(payload: ExecutionPlanInput) -> ExecutionPlan:
        return ExecutionPlan(
            plan_id=payload.plan_id,
            task_id=payload.task_id,
            steps=tuple(
                ExecutionStep(
                    step_id=item.step_id,
                    adapter=item.adapter,
                    operation=item.operation,
                    agent_role=item.agent_role,
                    capability=item.capability,
                    required_permission=item.required_permission,
                    inputs=(),
                    idempotent=item.idempotent,
                    max_retries=item.max_retries,
                )
                for item in payload.steps
            ),
            max_steps=payload.max_steps,
        )

    def execution(self, execution_id: str) -> object:
        if self.execution_repository is None:
            raise RuntimeError("execution repository is not configured")
        session = self.execution_repository.get_execution_session(execution_id)
        return {
            "execution_id": session.execution_id,
            "plan_id": session.plan_id,
            "task_id": session.task_id,
            "status": session.outcome.value if session.outcome is not None else "RUNNING",
            "started_at": session.started_at.isoformat(),
            "updated_at": session.updated_at.isoformat(),
            "event_count": len(session.events),
            "result_count": len(session.results),
            "blocking_finding_count": len(session.blocking_findings),
        }

    def audit(self, role: AgentRole, *, limit: int, trace_id: str | None = None) -> object:
        if self.observability is None:
            raise RuntimeError("observability service is not configured")
        context = AuditQueryContext(role, Permission.READ_CONTROL)
        filters = RuntimeEventFilter(trace_id=trace_id) if trace_id else None
        return _serialize(self.observability.list(context=context, filters=filters, limit=limit))

    def metrics(self, role: AgentRole) -> object:
        if self.monitoring is None:
            raise RuntimeError("monitoring service is not configured")
        context = MonitoringQueryContext(role, Permission.READ_CONTROL)
        return _serialize(self.monitoring.metrics(context=context))

    def health(self, role: AgentRole) -> object:
        if self.monitoring is None:
            status = "UNAVAILABLE" if self.config.environment.value == "production" else "UNKNOWN"
            return {"status": status, "reason_code": "MONITORING_UNAVAILABLE", "checks": []}
        context = MonitoringQueryContext(role, Permission.READ_CONTROL)
        return _serialize(self.monitoring.health(context=context))
