from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_os.api import digest_token
from ai_os.api.server import build_app


def test_server_requires_digest_and_uses_server_side_role(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("AIOS_API_TOKEN_SHA256", raising=False)
    with pytest.raises(ValueError, match="TOKEN_SHA256"):
        build_app(tmp_path)

    token = "server-side-test-token"
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
