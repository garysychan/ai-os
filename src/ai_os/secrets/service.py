"""Authorized fail-closed secret resolution service."""

from ai_os.agents import AgentRole, Permission

from .errors import SecretAuthorizationError, SecretNotFoundError
from .models import SecretAccessContext, SecretMaterial, SecretReference
from .protocol import SecretProvider


class SecretService:
    def __init__(self, provider: SecretProvider) -> None:
        self.provider = provider

    def check(self, reference: SecretReference, *, context: SecretAccessContext) -> bool:
        self._authorize(context)
        value = self.provider.resolve(reference)
        return value is not None and bool(value.strip())

    def resolve(
        self, reference: SecretReference, *, context: SecretAccessContext
    ) -> SecretMaterial:
        self._authorize(context)
        value = self.provider.resolve(reference)
        if value is None or not value.strip():
            raise SecretNotFoundError(f"required secret is unavailable: {reference.redacted}")
        return SecretMaterial(value)

    def _authorize(self, context: SecretAccessContext) -> None:
        if (
            context.actor_role is not AgentRole.CONTROLLER
            or context.permission is not Permission.COORDINATE
        ):
            raise SecretAuthorizationError("caller is not authorized to resolve secrets")
