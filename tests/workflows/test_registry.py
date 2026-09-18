"""Workflow definition and Registry tests."""

from dataclasses import replace

import pytest

from ai_os.agents import Permission
from ai_os.workflows import (
    WorkflowRegistry,
    WorkflowRegistryError,
    WorkflowValidationError,
    coding_workflow,
)


def test_registry_is_versioned_explicit_and_default_deny() -> None:
    definition = coding_workflow()
    registry = WorkflowRegistry((definition,))
    assert registry.resolve("coding", "1") is definition
    assert registry.list_definitions() == (definition,)
    with pytest.raises(WorkflowRegistryError, match="unknown Workflow"):
        registry.resolve("investment", "1")
    with pytest.raises(WorkflowRegistryError, match="duplicate"):
        registry.register(definition)


def test_definition_rejects_permission_driver_budget_and_duplicate_stage() -> None:
    definition = coding_workflow()
    stage = definition.stages[0]
    with pytest.raises(WorkflowValidationError, match="requires modify_code"):
        WorkflowRegistry(
            (
                replace(
                    definition,
                    stages=(replace(stage, required_permission=Permission.READ_CONTROL),),
                ),
            )
        )
    with pytest.raises(WorkflowValidationError, match="unsupported Workflow driver"):
        WorkflowRegistry((replace(definition, driver="arbitrary_python"),))
    with pytest.raises(WorkflowValidationError, match="step budget"):
        WorkflowRegistry((replace(definition, max_steps=1),))
    with pytest.raises(WorkflowValidationError, match="unique"):
        WorkflowRegistry((replace(definition, stages=(stage, stage)),))
    with pytest.raises(WorkflowValidationError, match="canonical"):
        WorkflowRegistry((replace(definition, stages=(stage,)),))
