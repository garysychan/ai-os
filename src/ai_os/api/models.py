"""Strict versioned HTTP contracts."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ai_os.agents import AgentRole, Capability, Permission


class StrictModel(BaseModel):
    # FastAPI validates decoded JSON as Python values. Enum strings therefore need
    # canonical enum parsing while unknown fields and schema versions still fail closed.
    model_config = ConfigDict(extra="forbid", frozen=True, strict=False)


class ErrorDetail(StrictModel):
    code: str
    message: str


class ErrorEnvelope(StrictModel):
    schema_version: Literal[1] = 1
    request_id: str
    error: ErrorDetail


class ResponseEnvelope(StrictModel):
    schema_version: Literal[1] = 1
    request_id: str
    data: Any
    meta: dict[str, Any] = Field(default_factory=dict)


class WorkflowStageInput(StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    agent_role: AgentRole
    capability: Capability
    required_permission: Permission


class WorkflowInput(StrictModel):
    schema_version: Literal[1] = 1
    name: str = Field(pattern=r"^[a-z][a-z0-9-]{0,63}$")
    version: str = Field(pattern=r"^[0-9]+(?:\.[0-9]+){0,2}$")
    description: str = Field(min_length=1, max_length=1_000)
    driver: str = Field(min_length=1, max_length=100)
    stages: tuple[WorkflowStageInput, ...] = Field(min_length=1, max_length=64)
    max_steps: int = Field(ge=1, le=256)
    max_fix_attempts: int = Field(ge=0, le=32)
    approval_required: bool = False
    required_output_sections: tuple[str, ...] = Field(default=(), max_length=32)


class ExecutionStepInput(StrictModel):
    step_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,99}$")
    adapter: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    operation: str = Field(pattern=r"^[a-z][a-z0-9_]{0,63}$")
    agent_role: AgentRole
    capability: Capability
    required_permission: Permission
    idempotent: bool = False
    max_retries: int = Field(default=0, ge=0, le=10)


class ExecutionPlanInput(StrictModel):
    schema_version: Literal[1] = 1
    plan_id: str = Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,199}$")
    task_id: str = Field(pattern=r"^TASK-[0-9]{4,}$")
    steps: tuple[ExecutionStepInput, ...] = Field(min_length=1, max_length=256)
    max_steps: int = Field(ge=1, le=256)
