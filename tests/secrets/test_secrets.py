import pytest

from ai_os.agents import AgentRole, Permission
from ai_os.secrets import (
    EnvironmentSecretProvider,
    SecretAccessContext,
    SecretAuthorizationError,
    SecretMaterial,
    SecretNotFoundError,
    SecretReference,
    SecretReferenceError,
    SecretService,
    redact_text,
)


def _context() -> SecretAccessContext:
    return SecretAccessContext(AgentRole.CONTROLLER, Permission.COORDINATE)


def test_reference_and_environment_provider_are_explicit() -> None:
    reference = SecretReference.parse("env://AI_API_KEY")
    provider = EnvironmentSecretProvider({"AI_API_KEY": "very-secret"})
    assert provider.resolve(reference) == "very-secret"
    with pytest.raises(SecretReferenceError):
        SecretReference.parse("AI_API_KEY=very-secret")
    with pytest.raises(SecretReferenceError):
        SecretReference("unsafe", "AI_API_KEY")
    with pytest.raises(SecretReferenceError):
        SecretReference("env", "lowercase")


def test_authorized_resolution_returns_opaque_material() -> None:
    service = SecretService(EnvironmentSecretProvider({"AI_API_KEY": "very-secret"}))
    material = service.resolve(SecretReference.parse("env://AI_API_KEY"), context=_context())
    assert isinstance(material, SecretMaterial)
    assert material.reveal() == "very-secret"
    assert str(material) == "[REDACTED]"
    assert "very-secret" not in repr(material)


def test_unauthorized_or_missing_resolution_fails_closed() -> None:
    reference = SecretReference.parse("env://AI_API_KEY")
    service = SecretService(EnvironmentSecretProvider({}))
    with pytest.raises(SecretAuthorizationError):
        service.resolve(
            reference,
            context=SecretAccessContext(AgentRole.REVIEWER, Permission.READ_CONTROL),
        )
    with pytest.raises(SecretNotFoundError) as caught:
        service.resolve(reference, context=_context())
    assert "very-secret" not in str(caught.value)
    assert service.check(reference, context=_context()) is False


def test_redaction_covers_headers_assignments_and_embedded_values() -> None:
    output = redact_text(
        "Authorization: Bearer top-secret\n"
        "Proxy-Authorization: Basic dXNlcjpwYXNz\n"
        "X-API-Key: abc\n"
        "token=assigned-secret note=embedded-secret",
        secret_values=("embedded-secret",),
    )
    assert "top-secret" not in output
    assert "dXNlcjpwYXNz" not in output
    assert "abc" not in output
    assert "assigned-secret" not in output
    assert "embedded-secret" not in output
    assert output.count("[REDACTED]") == 5
