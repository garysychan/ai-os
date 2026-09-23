"""Private loopback ASGI server entry point."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from ai_os.agents import AgentRole
from ai_os.config import EnvironmentProfile

from .app import create_app
from .auth import CredentialBinding, StaticBearerAuthenticator
from .config import ApiConfig


def build_app(
    root: Path,
    *,
    environment: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT,
) -> FastAPI:
    """Build an authenticated app without accepting secret material as CLI arguments."""

    digest = os.environ.get("AIOS_API_TOKEN_SHA256", "").strip().lower()
    role_value = os.environ.get("AIOS_API_ROLE", AgentRole.CONTROLLER.value)
    principal_id = os.environ.get("AIOS_API_PRINCIPAL_ID", "local-operator").strip()
    credential_id = os.environ.get("AIOS_API_CREDENTIAL_ID", "local-bearer").strip()
    if not digest:
        raise ValueError("AIOS_API_TOKEN_SHA256 is required")
    try:
        role = AgentRole(role_value)
    except ValueError as error:
        raise ValueError("AIOS_API_ROLE must be a canonical AgentRole") from error
    authentication = StaticBearerAuthenticator(
        (CredentialBinding(credential_id, digest, principal_id, role),)
    )
    return create_app(ApiConfig(root=root.resolve(), environment=environment), authentication)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the governed AI OS Runtime API.")
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--environment",
        choices=[item.value for item in EnvironmentProfile],
        default=EnvironmentProfile.DEVELOPMENT.value,
    )
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args(argv)
    config = ApiConfig(
        root=args.root.resolve(),
        port=args.port,
        environment=EnvironmentProfile(args.environment),
    )
    application = build_app(config.root, environment=config.environment)
    uvicorn.run(application, host=config.host, port=config.port, access_log=False)
    return 0
