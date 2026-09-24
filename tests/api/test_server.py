from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_os.api import digest_token
from ai_os.api.server import build_app
from ai_os.config import EnvironmentProfile


def test_server_requires_strong_token_and_uses_server_side_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIOS_API_TOKEN_SHA256", raising=False)
    with pytest.raises(ValueError, match="at least 32 bytes"):
        build_app(tmp_path)

    token = "server-side-test-token-with-32-byte-minimum"
    monkeypatch.setenv("AIOS_API_TOKEN_SHA256", digest_token(token))
    monkeypatch.setenv("AIOS_API_ROLE", "Controller")
    application = build_app(tmp_path)
    response = TestClient(application).get(
        "/v1/version", headers={"Authorization": f"Bearer {token}"}
    )

    assert response.status_code == 200


def test_server_rejects_noncanonical_role(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AIOS_API_TOKEN_SHA256", digest_token("token"))
    monkeypatch.setenv("AIOS_API_ROLE", "Administrator")

    with pytest.raises(ValueError, match="canonical AgentRole"):
        build_app(tmp_path)


def test_production_requires_secret_backed_strong_token(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIOS_API_TOKEN_REF", raising=False)
    monkeypatch.delenv("AIOS_API_TOKEN_SHA256", raising=False)
    with pytest.raises(ValueError, match="token reference"):
        build_app(tmp_path, environment=EnvironmentProfile.PRODUCTION)

    monkeypatch.setenv("AIOS_API_TOKEN_REF", "env://AIOS_TEST_API_TOKEN")
    monkeypatch.setenv("AIOS_TEST_API_TOKEN", "synthetic-production-token-with-32-bytes")
    application = build_app(
        tmp_path,
        environment=EnvironmentProfile.PRODUCTION,
    )
    assert application.state.services.execution_repository is not None
    assert application.state.services.observability is not None
    assert application.state.services.monitoring is not None
    response = TestClient(application).get(
        "/v1/health",
        headers={"Authorization": "Bearer synthetic-production-token-with-32-bytes"},
    )
    assert response.status_code == 200
    assert response.json()["data"]["status"] == "UNAVAILABLE"

    monkeypatch.setenv("AIOS_TEST_API_TOKEN", "weak")
    with pytest.raises(ValueError, match="32 bytes"):
        build_app(
            tmp_path,
            environment=EnvironmentProfile.PRODUCTION,
        )
