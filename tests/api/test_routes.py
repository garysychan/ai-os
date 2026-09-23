from typing import cast

from fastapi import FastAPI
from fastapi.testclient import TestClient


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
    assert task.json()["data"]["status"] == "IN_PROGRESS"
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
