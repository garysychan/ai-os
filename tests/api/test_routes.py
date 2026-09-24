import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient

from ai_os.agents import AgentRole
from ai_os.api import ApiConfig, create_app
from ai_os.api.services import RuntimeApiServices
from ai_os.execution import (
    ExecutionEvent,
    ExecutionEventType,
    ExecutionSession,
    StepResult,
    StepStatus,
)
from ai_os.persistence import SQLiteRuntimeStore, StoreConfig

TEST_TOKEN = "synthetic-execution-token-with-32-byte-minimum"


def test_system_and_catalog_routes_are_versioned_and_bounded(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    version = client.get("/v1/version", headers=auth_headers)
    capabilities = client.get("/v1/capabilities", headers=auth_headers)
    agents = client.get("/v1/agents", headers=auth_headers)
    workflows = client.get("/v1/workflows", headers=auth_headers)

    assert version.status_code == 200
    assert version.json()["schema_version"] == 1
    assert version.json()["data"]["api_version"] == "v1"
    assert capabilities.json()["data"]["mutation"] is False
    assert capabilities.json()["data"]["execution_dispatch"] is False
    assert len(agents.json()["data"]) == 7
    assert {item["name"] for item in workflows.json()["data"]} >= {
        "coding",
        "trace",
        "investment",
        "deep-research",
    }
    assert version.headers["cache-control"] == "no-store"
    assert version.headers["x-request-id"].startswith("req-")
    evidence = cast(FastAPI, client.app).state.audit.list(limit=1)[0]
    assert evidence.route == "/v1/workflows"
    assert evidence.agent_role == "Controller"
    assert evidence.outcome == "SUCCESS"


def test_control_plane_and_task_routes_reuse_authoritative_loader(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    status = client.get("/v1/control-plane/status", headers=auth_headers)
    task = client.get("/v1/tasks/TASK-0021", headers=auth_headers)
    tasks = client.get("/v1/tasks?offset=0&limit=2", headers=auth_headers)

    assert status.status_code == 200
    assert "TASKS.md" in status.json()["data"]["documents"]
    assert task.status_code == 200
    assert task.json()["data"]["status"] == "DONE"
    assert tasks.status_code == 200
    assert len(tasks.json()["data"]) == 2
    assert tasks.json()["meta"]["total"] >= 21


def test_unknown_resource_and_query_bounds_use_redacted_errors(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    missing = client.get("/v1/tasks/TASK-9999", headers=auth_headers)
    oversized = client.get("/v1/tasks?limit=101", headers=auth_headers)

    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "RESOURCE_NOT_FOUND"
    assert oversized.status_code == 422
    assert oversized.json()["error"]["code"] == "QUERY_BOUND_EXCEEDED"


def test_unknown_request_fields_fail_closed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/v1/executions/validate",
        headers=auth_headers,
        json={
            "schema_version": 1,
            "plan_id": "plan-1",
            "task_id": "TASK-0021",
            "steps": [],
            "max_steps": 1,
            "actor_role": "Controller",
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == "request validation failed"
    assert "actor_role" not in response.text


def test_actual_request_body_size_is_bounded(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    response = client.post(
        "/v1/executions/validate",
        headers={**auth_headers, "content-length": "70000"},
        content=b"{}",
    )

    assert response.status_code == 413
    assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"


def test_execution_projection_excludes_private_session_payloads(tmp_path: Path) -> None:
    store = SQLiteRuntimeStore(StoreConfig(tmp_path / "runtime.db"))
    store.initialize()
    instant = datetime.now(UTC)
    store.save_execution_session(
        ExecutionSession(
            execution_id="execution-sensitive",
            plan_id="plan-1",
            task_id="TASK-0021",
            controller_session_id="controller-1",
            started_at=instant,
            updated_at=instant,
            events=(
                ExecutionEvent(
                    1,
                    "execution-sensitive",
                    "TASK-0021",
                    ExecutionEventType.SESSION_FINISHED,
                    instant,
                    "PRIVATE_EXCEPTION_VALUE",
                    evidence=("PRIVATE_RAW_EVIDENCE",),
                ),
            ),
            results=(
                StepResult(
                    "step-1",
                    1,
                    StepStatus.FAILED,
                    "PRIVATE_RESULT_SUMMARY",
                    outputs=(("private_output", "PRIVATE_OUTPUT_VALUE"),),
                    errors=("PRIVATE_ERROR_VALUE",),
                ),
            ),
            blocking_findings=("PRIVATE_FINDING_VALUE",),
        )
    )
    config = ApiConfig(root=Path(__file__).resolve().parents[2])
    services = RuntimeApiServices(config, execution_repository=store)
    application = create_app(config, _authenticator(), services=services)
    response = TestClient(application).get(
        "/v1/executions/execution-sensitive",
        headers={"Authorization": "Bearer " + TEST_TOKEN},
    )

    assert response.status_code == 200
    body = response.text
    assert "PRIVATE_" not in body
    assert set(response.json()["data"]) == {
        "execution_id",
        "plan_id",
        "task_id",
        "status",
        "started_at",
        "updated_at",
        "event_count",
        "result_count",
        "blocking_finding_count",
    }


def test_streaming_body_limit_handles_exact_and_falsified_lengths(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    limit = client.app.state.config.max_request_bytes
    exact = client.post(
        "/v1/executions/validate",
        headers={**auth_headers, "content-length": str(limit - 1)},
        content=b"x" * limit,
    )
    oversized = client.post(
        "/v1/executions/validate",
        headers={**auth_headers, "content-length": str(limit)},
        content=b"x" * (limit + 1),
    )

    assert exact.status_code != 413
    assert oversized.status_code == 413


def test_streaming_body_without_content_length_is_rejected(client: TestClient) -> None:
    limit = client.app.state.config.max_request_bytes
    sent: list[dict[str, object]] = []
    chunks = iter((b"x" * limit, b"x"))

    async def receive() -> dict[str, object]:
        try:
            chunk = next(chunks)
        except StopIteration:
            return {"type": "http.disconnect"}
        return {"type": "http.request", "body": chunk, "more_body": chunk == b"x" * limit}

    async def send(message: dict[str, object]) -> None:
        sent.append(message)

    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "POST",
        "scheme": "http",
        "path": "/v1/executions/validate",
        "raw_path": b"/v1/executions/validate",
        "query_string": b"",
        "headers": [(b"authorization", b"Bearer " + TEST_TOKEN.encode())],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
        "root_path": "",
    }
    asyncio.run(client.app(scope, receive, send))

    assert sent[0]["status"] == 413


def _authenticator():
    from ai_os.api import CredentialBinding, StaticBearerAuthenticator, digest_token

    return StaticBearerAuthenticator(
        (
            CredentialBinding(
                "test", digest_token(TEST_TOKEN), "test-principal", AgentRole.CONTROLLER
            ),
        )
    )
