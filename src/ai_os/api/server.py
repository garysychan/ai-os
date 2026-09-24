"""Private loopback ASGI server entry point."""

from __future__ import annotations

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from fastapi import FastAPI

from ai_os.agents import AgentRole, Permission
from ai_os.config import EnvironmentProfile, load_config
from ai_os.monitoring import MonitoringService
from ai_os.observability import ObservabilityService
from ai_os.persistence import SQLiteRuntimeStore, StoreConfig
from ai_os.secrets import (
    EnvironmentSecretProvider,
    SecretAccessContext,
    SecretReference,
    SecretService,
)
from ai_os.workflows import WorkflowRegistry, core_workflows

from .app import create_app
from .auth import CredentialBinding, StaticBearerAuthenticator, digest_token
from .config import ApiConfig
from .services import RuntimeApiServices


def build_app(
    root: Path,
    *,
    environment: EnvironmentProfile = EnvironmentProfile.DEVELOPMENT,
) -> FastAPI:
    """Build an authenticated app without accepting secret material as CLI arguments."""

    digest = _resolve_digest(environment)
    role_value = os.environ.get("AIOS_API_ROLE", AgentRole.CONTROLLER.value)
    principal_id = os.environ.get("AIOS_API_PRINCIPAL_ID", "local-operator").strip()
    credential_id = os.environ.get("AIOS_API_CREDENTIAL_ID", "local-bearer").strip()
    try:
        role = AgentRole(role_value)
    except ValueError as error:
        raise ValueError("AIOS_API_ROLE must be a canonical AgentRole") from error
    authentication = StaticBearerAuthenticator(
        (CredentialBinding(credential_id, digest, principal_id, role),)
    )
    runtime_config = load_config(profile=environment)
    database = root / runtime_config.database_path
    store = SQLiteRuntimeStore(StoreConfig(database=database))
    store.initialize()
    api_config = ApiConfig(root=root.resolve(), environment=environment)
    services = RuntimeApiServices(
        api_config,
        execution_repository=store,
        observability=ObservabilityService(store),
        monitoring=MonitoringService(store),
        workflow_registry_service=WorkflowRegistry(core_workflows()),
    )
    return create_app(api_config, authentication, services=services)


def _resolve_digest(environment: EnvironmentProfile) -> str:
    if environment is not EnvironmentProfile.PRODUCTION:
        configured_digest = os.environ.get("AIOS_API_TOKEN_SHA256", "").strip().lower()
        if configured_digest:
            if len(configured_digest) != 64 or any(
                character not in "0123456789abcdef" for character in configured_digest
            ):
                raise ValueError("API bearer token digest is invalid")
            return configured_digest
    reference_value = os.environ.get("AIOS_API_TOKEN_REF", "").strip()
    if not reference_value:
        if environment is EnvironmentProfile.PRODUCTION:
            raise ValueError("production API bearer token reference is required")
        token = os.environ.get("AIOS_API_TOKEN", "")
    else:
        try:
            reference = SecretReference.parse(reference_value)
            token = (
                SecretService(EnvironmentSecretProvider())
                .resolve(
                    reference,
                    context=SecretAccessContext(AgentRole.CONTROLLER, Permission.COORDINATE),
                )
                .reveal()
            )
        except Exception as error:
            raise ValueError("API bearer token could not be resolved") from error
    if len(token.encode("utf-8")) < 32:
        raise ValueError("API bearer token must contain at least 32 bytes")
    return digest_token(token)


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
