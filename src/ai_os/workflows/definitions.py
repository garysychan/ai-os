"""Built-in Workflow definitions with no provider-specific behavior."""

from ai_os.agents import AgentRole, Capability, Permission

from .models import WorkflowDefinition, WorkflowStage


def coding_workflow() -> WorkflowDefinition:
    return WorkflowDefinition(
        name="coding",
        version="1",
        description="Governed Developer, Tester, Reviewer and finite Fixer lifecycle.",
        driver="controller_lifecycle",
        stages=(
            WorkflowStage(
                "implement", AgentRole.DEVELOPER, Capability.IMPLEMENT, Permission.MODIFY_CODE
            ),
            WorkflowStage("test", AgentRole.TESTER, Capability.TEST, Permission.READ_CONTROL),
            WorkflowStage(
                "review", AgentRole.REVIEWER, Capability.REVIEW, Permission.APPROVE_REVIEW
            ),
            WorkflowStage("fix", AgentRole.FIXER, Capability.FIX, Permission.MODIFY_CODE),
        ),
        max_steps=8,
        max_fix_attempts=2,
    )


def core_workflows() -> tuple[WorkflowDefinition, ...]:
    return (coding_workflow(),)
