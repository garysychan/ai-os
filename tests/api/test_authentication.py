from pathlib import Path
from typing import cast

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_os.agents import AgentRole
from ai_os.api import (
    ApiConfig,
    CredentialBinding,
    StaticBearerAuthenticator,
    create_app,
    digest_token,
)


def test_missing_and_invalid_credentials_fail_closed(client: TestClient) -> None:
    missing = client.get("/v1/version")
    invalid = client.get("/v1/version", headers={"Authorization": "Bearer wrong"})

    assert missing.status_code == 401
    assert invalid.status_code == 401
    assert missing.json()["error"]["code"] == "AUTHENTICATION_REQUIRED"
    assert invalid.json()["error"]["code"] == "AUTHENTICATION_FAILED"
    assert "wrong" not in invalid.text
    events = cast(FastAPI, client.app).state.audit.list(limit=2)
    assert [item.outcome for item in events] == ["DENIED", "DENIED"]
    assert all(item.agent_role is None for item in events)


def test_client_supplied_role_cannot_change_server_principal(client: TestClient) -> None:
    response = client.get(
        "/v1/version",
        headers={"Authorization": "Bearer wrong", "X-Actor-Role": "Controller"},
    )

    assert response.status_code == 401
    assert cast(FastAPI, client.app).state.audit.list(limit=1)[0].agent_role is None


def test_role_without_required_permission_is_denied() -> None:
    root = Path(__file__).resolve().parents[2]
    token = "credential-for-no-authority"
    authenticator = StaticBearerAuthenticator(
        (
            CredentialBinding(
                "limited",
                digest_token(token),
                "limited-principal",
                AgentRole("Controller"),
            ),
        )
    )
    application = create_app(ApiConfig(root=root), authenticator)
    policy = pytest.MonkeyPatch()
    try:
        policy.setattr("ai_os.api.app.PermissionPolicy.allows", lambda *_: False)
        response = TestClient(application).get(
            "/v1/version", headers={"Authorization": f"Bearer {token}"}
        )
    finally:
        policy.undo()

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTHORIZATION_DENIED"


def test_duplicate_or_malformed_bindings_are_rejected() -> None:
    digest = digest_token("one-credential")
    with pytest.raises(ValueError, match="unique"):
        StaticBearerAuthenticator(
            (
                CredentialBinding("one", digest, "p1", AgentRole.CONTROLLER),
                CredentialBinding("two", digest, "p2", AgentRole.PLANNER),
            )
        )
    with pytest.raises(ValueError, match="SHA-256"):
        CredentialBinding("one", "plaintext", "p1", AgentRole.CONTROLLER)
