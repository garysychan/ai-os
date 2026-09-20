"""Investment research workflow definition."""

from ai_os.agents import AgentRole, Capability, Permission

from ..models import WorkflowDefinition, WorkflowStage


def investment_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="investment",
        version="1.0.0",
        description="Governed evidence, valuation and risk analysis with independent review.",
        driver="linear_stage_plan",
        stages=(
            WorkflowStage("scope", AgentRole.PLANNER, Capability.PLAN, Permission.PROPOSE_CHANGE),
            WorkflowStage(
                "research", AgentRole.RESEARCHER, Capability.RESEARCH, Permission.READ_CONTROL
            ),
            WorkflowStage(
                "valuation", AgentRole.RESEARCHER, Capability.RESEARCH, Permission.READ_CONTROL
            ),
            WorkflowStage(
                "risk", AgentRole.RESEARCHER, Capability.RESEARCH, Permission.READ_CONTROL
            ),
            WorkflowStage(
                "review", AgentRole.REVIEWER, Capability.REVIEW, Permission.APPROVE_REVIEW
            ),
        ),
        max_steps=5,
        max_fix_attempts=0,
        approval_required=False,
        required_output_sections=("facts", "inference", "assumptions"),
    )
