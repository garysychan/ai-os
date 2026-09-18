"""TRACE evidence workflow definition."""

from ai_os.agents import AgentRole, Capability, Permission

from ..models import WorkflowDefinition, WorkflowStage


def trace_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="trace",
        version="1.0.0",
        description="Plan, gather, synthesize and independently review traceable evidence.",
        driver="linear_stage_plan",
        stages=(
            WorkflowStage("plan", AgentRole.PLANNER, Capability.PLAN, Permission.PROPOSE_CHANGE),
            WorkflowStage(
                "gather", AgentRole.RESEARCHER, Capability.RESEARCH, Permission.READ_CONTROL
            ),
            WorkflowStage(
                "synthesize", AgentRole.PLANNER, Capability.PLAN, Permission.PROPOSE_CHANGE
            ),
            WorkflowStage(
                "review", AgentRole.REVIEWER, Capability.REVIEW, Permission.APPROVE_REVIEW
            ),
        ),
        max_steps=4,
        max_fix_attempts=0,
        approval_required=False,
        required_output_sections=("evidence", "sources", "conclusions"),
    )
