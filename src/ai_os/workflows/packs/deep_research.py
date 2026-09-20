"""Deep Research workflow definition."""

from ai_os.agents import AgentRole, Capability, Permission

from ..models import WorkflowDefinition, WorkflowStage


def deep_research_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="deep-research",
        version="1.0.0",
        description="Plan, collect, triangulate and synthesize research with independent review.",
        driver="linear_stage_plan",
        stages=(
            WorkflowStage("plan", AgentRole.PLANNER, Capability.PLAN, Permission.PROPOSE_CHANGE),
            WorkflowStage(
                "collect", AgentRole.RESEARCHER, Capability.RESEARCH, Permission.READ_CONTROL
            ),
            WorkflowStage(
                "triangulate", AgentRole.RESEARCHER, Capability.RESEARCH, Permission.READ_CONTROL
            ),
            WorkflowStage(
                "analyze", AgentRole.RESEARCHER, Capability.RESEARCH, Permission.READ_CONTROL
            ),
            WorkflowStage(
                "synthesize", AgentRole.PLANNER, Capability.PLAN, Permission.PROPOSE_CHANGE
            ),
            WorkflowStage(
                "review", AgentRole.REVIEWER, Capability.REVIEW, Permission.APPROVE_REVIEW
            ),
        ),
        max_steps=6,
        max_fix_attempts=0,
        approval_required=False,
        required_output_sections=("facts", "inference", "assumptions"),
    )
