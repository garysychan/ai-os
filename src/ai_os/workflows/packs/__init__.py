"""Governed built-in Workflow Definition Packs."""

from ..models import WorkflowDefinition
from .deep_research import deep_research_workflow
from .investment import investment_workflow
from .trace import trace_workflow


def workflow_packs() -> tuple[WorkflowDefinition, ...]:
    return (trace_workflow(), investment_workflow(), deep_research_workflow())


__all__ = [
    "deep_research_workflow",
    "investment_workflow",
    "trace_workflow",
    "workflow_packs",
]
