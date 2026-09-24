from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from ai_os.agents import AgentRole
from ai_os.api import (
    ApiConfig,
    CredentialBinding,
    StaticBearerAuthenticator,
    create_app,
    digest_token,
)
from ai_os.api.audit import ApiAuditRecorder
from ai_os.api.services import RuntimeApiServices
from ai_os.monitoring import MonitoringService
from ai_os.observability import (
    ObservabilityService,
    RuntimeEvent,
    RuntimeEventSource,
    RuntimeEventType,
)
from ai_os.persistence import SQLiteRuntimeStore, StoreConfig


def test_api_audit_is_persisted_redacted_and_principal_specific(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(StoreConfig(tmp_path / "audit.db"))
    store.initialize()
    observability = ObservabilityService(store)
    config = ApiConfig(root=Path(__file__).resolve().parents[2])

    def application(principal_id: str, token: str):
        services = RuntimeApiServices(config, observability=observability, monitoring=None)
        authentication = StaticBearerAuthenticator(
            (
                CredentialBinding(
                    "credential-" + principal_id,
                    digest_token(token),
                    principal_id,
                    AgentRole.CONTROLLER,
                ),
            )
        )
        return create_app(config, authentication, services=services)

    TestClient(application("principal-one", "synthetic-audit-token-one-with-32-bytes")).get(
        "/v1/version?private=PRIVATE_QUERY_VALUE",
        headers={"Authorization": "Bearer synthetic-audit-token-one-with-32-bytes"},
    )
    TestClient(application("principal-two", "synthetic-audit-token-two-with-32-bytes")).get(
        "/v1/version",
        headers={"Authorization": "Bearer synthetic-audit-token-two-with-32-bytes"},
    )
    failed = TestClient(
        application("principal-one", "synthetic-audit-token-one-with-32-bytes")
    ).get("/v1/version", headers={"Authorization": "Bearer invalid-private-token"})
    assert failed.status_code == 401

    events = ApiAuditRecorder(100, observability).list(limit=10)
    assert {event.principal_id for event in events if event.status_code == 200} >= {
        "principal-one",
        "principal-two",
    }
    assert any(event.status_code == 401 and event.outcome == "DENIED" for event in events)
    assert all(event.route == "/v1/version" for event in events)
    stored = str(store.list_runtime_events(limit=10))
    assert "synthetic-audit-token" not in stored
    assert "PRIVATE_QUERY_VALUE" not in stored


def test_configured_monitoring_evidence_reports_healthy(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(StoreConfig(tmp_path / "health.db"))
    store.initialize()
    store.append_runtime_event(
        RuntimeEvent(
            event_id="health-event",
            sequence=0,
            timestamp=datetime.now(UTC),
            event_type=RuntimeEventType.COMPLETED,
            source=RuntimeEventSource.GOVERNANCE,
            task_id="TASK-0021",
            trace_id="health-trace",
            summary="healthy evidence",
        )
    )
    config = ApiConfig(root=Path(__file__).resolve().parents[2])
    services = RuntimeApiServices(
        config,
        observability=ObservabilityService(store),
        monitoring=MonitoringService(store),
    )
    authentication = StaticBearerAuthenticator(
        (
            CredentialBinding(
                "health-credential",
                digest_token("synthetic-health-token-with-32-bytes"),
                "health-principal",
                AgentRole.CONTROLLER,
            ),
        )
    )
    response = TestClient(create_app(config, authentication, services=services)).get(
        "/v1/health",
        headers={"Authorization": "Bearer synthetic-health-token-with-32-bytes"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "HEALTHY"
