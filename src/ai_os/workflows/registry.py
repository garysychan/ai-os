"""Versioned, explicit and default-deny Workflow Registry."""

from .errors import WorkflowRegistryError
from .models import WorkflowDefinition
from .validation import validate_definition


class WorkflowRegistry:
    def __init__(self, definitions: tuple[WorkflowDefinition, ...] = ()) -> None:
        self._definitions: dict[tuple[str, str], WorkflowDefinition] = {}
        for definition in definitions:
            self.register(definition)

    def register(self, definition: WorkflowDefinition) -> None:
        validate_definition(definition)
        key = (definition.name, definition.version)
        if key in self._definitions:
            raise WorkflowRegistryError(
                f"duplicate Workflow registration: {definition.name}@{definition.version}"
            )
        self._definitions[key] = definition

    def resolve(self, name: str, version: str) -> WorkflowDefinition:
        try:
            return self._definitions[(name, version)]
        except KeyError as error:
            raise WorkflowRegistryError(f"unknown Workflow: {name}@{version}") from error

    def list_definitions(self) -> tuple[WorkflowDefinition, ...]:
        return tuple(self._definitions[key] for key in sorted(self._definitions))
