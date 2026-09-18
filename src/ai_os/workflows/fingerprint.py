"""Stable identity for an exact executable Workflow definition."""

import json
from hashlib import sha256

from .models import WorkflowDefinition


def definition_fingerprint(definition: WorkflowDefinition) -> str:
    payload = {
        "name": definition.name,
        "version": definition.version,
        "driver": definition.driver,
        "max_steps": definition.max_steps,
        "max_fix_attempts": definition.max_fix_attempts,
        "approval_required": definition.approval_required,
        "required_output_sections": definition.required_output_sections,
        "stages": [
            {
                "name": stage.name,
                "role": stage.agent_role.value,
                "capability": stage.capability.value,
                "permission": stage.required_permission.value,
            }
            for stage in definition.stages
        ],
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return sha256(encoded).hexdigest()
