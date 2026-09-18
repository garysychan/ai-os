"""Definition Pack validation and registry tests."""

from dataclasses import replace

import pytest

from ai_os.agents import AgentRole, Capability, Permission
from ai_os.workflows import (
    WorkflowDefinition,
    WorkflowRegistry,
    WorkflowStage,
    WorkflowValidationError,
    core_workflows,
    validate_definition,
)
from ai_os.workflows.packs import (
    deep_research_workflow,
    investment_workflow,
    trace_workflow,
)


def test_all_versioned_packs_are_registered_and_valid() -> None:
    registry = WorkflowRegistry(core_workflows())
    assert registry.resolve("trace", "1.0.0") == trace_workflow()
    assert registry.resolve("investment", "1.0.0") == investment_workflow()
    assert registry.resolve("deep-research", "1.0.0") == deep_research_workflow()
    for definition in core_workflows()[1:]:
        validate_definition(definition)


def test_research_output_contract_distinguishes_evidence_types() -> None:
    for definition in (investment_workflow(), deep_research_workflow()):
        assert {"facts", "inference", "assumptions"} <= set(definition.required_output_sections)


@pytest.mark.parametrize(
    ("definition", "message"),
    [
        (replace(trace_workflow(), version="1"), "semantic versioning"),
        (replace(trace_workflow(), driver="unknown"), "unsupported Workflow driver"),
        (
            replace(trace_workflow(), stages=tuple(reversed(trace_workflow().stages))),
            "final Reviewer",
        ),
        (
            replace(
                trace_workflow(),
                stages=(
                    WorkflowStage(
                        "plan",
                        AgentRole.RESEARCHER,
                        Capability.PLAN,
                        Permission.PROPOSE_CHANGE,
                    ),
                    *trace_workflow().stages[1:],
                ),
            ),
            "cannot execute",
        ),
    ],
)
def test_invalid_pack_metadata_fails_closed(definition: WorkflowDefinition, message: str) -> None:
    with pytest.raises(WorkflowValidationError, match=message):
        validate_definition(definition)
