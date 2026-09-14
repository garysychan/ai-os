"""Backward-compatible access to the executable transition policy."""

from __future__ import annotations

from ai_os.workflow.transitions import (
    ALLOWED_TRANSITIONS as _RUNTIME_TRANSITIONS,
)
from ai_os.workflow.transitions import is_valid_transition

# Preserve the original governance API shape: pairs of state-name strings.
ALLOWED_TRANSITIONS = frozenset(
    (source.value, target.value)
    for source, target in _RUNTIME_TRANSITIONS
)

__all__ = ["ALLOWED_TRANSITIONS", "is_valid_transition"]
