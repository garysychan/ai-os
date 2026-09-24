from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from ai_os.agents import AgentRole
from ai_os.api import (
    ApiConfig,
    CredentialBinding,
    StaticBearerAuthenticator,
    create_app,
    digest_token,
)

TOKEN = "test-runtime-token-with-sufficient-entropy"


@pytest.fixture
def client() -> TestClient:
    root = Path(__file__).resolve().parents[2]
    config = ApiConfig(root=root, max_page_size=100)
    authentication = StaticBearerAuthenticator(
        (
            CredentialBinding(
                credential_id="test-controller",
                token_digest=digest_token(TOKEN),
                principal_id="api-test-controller",
                role=AgentRole.CONTROLLER,
            ),
        )
    )
    return TestClient(create_app(config, authentication), raise_server_exceptions=False)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    return {"Authorization": f"Bearer {TOKEN}"}
