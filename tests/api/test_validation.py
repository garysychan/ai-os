from fastapi.testclient import TestClient


def _workflow() -> dict[str, object]:
    return {
        "schema_version": 1,
        "name": "trace",
        "version": "1.0.0",
        "description": "Validated TRACE dry-run.",
        "driver": "linear_stage_plan",
        "stages": [
            {
                "name": "plan",
                "agent_role": "Planner",
                "capability": "plan",
                "required_permission": "propose_change",
            },
            {
                "name": "gather",
                "agent_role": "Researcher",
                "capability": "research",
                "required_permission": "read_control",
            },
            {
                "name": "synthesize",
                "agent_role": "Researcher",
                "capability": "research",
                "required_permission": "read_control",
            },
            {
                "name": "review",
                "agent_role": "Reviewer",
                "capability": "review",
                "required_permission": "approve_review",
            },
        ],
        "max_steps": 4,
        "max_fix_attempts": 0,
    }


def test_workflow_validate_and_dry_run_never_dispatch(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    validate = client.post("/v1/workflows/validate", headers=auth_headers, json=_workflow())
    dry_run = client.post("/v1/workflows/dry-run", headers=auth_headers, json=_workflow())

    assert validate.status_code == 200
    assert validate.json()["data"]["valid"] is True
    assert dry_run.status_code == 200
    assert dry_run.json()["data"]["dispatched"] is False
    assert len(dry_run.json()["data"]["stages"]) == 4


def test_execution_validate_and_dry_run_never_dispatch(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "schema_version": 1,
        "plan_id": "plan-0021",
        "task_id": "TASK-0021",
        "steps": [
            {
                "step_id": "inspect",
                "adapter": "file_read",
                "operation": "read",
                "agent_role": "Researcher",
                "capability": "research",
                "required_permission": "read_control",
                "idempotent": True,
                "max_retries": 0,
            }
        ],
        "max_steps": 1,
    }

    validate = client.post("/v1/executions/validate", headers=auth_headers, json=payload)
    dry_run = client.post("/v1/executions/dry-run", headers=auth_headers, json=payload)

    assert validate.status_code == 200
    assert validate.json()["data"]["valid"] is True
    assert dry_run.status_code == 200
    assert dry_run.json()["data"]["dispatched"] is False


def test_invalid_role_permission_pair_fails_closed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "schema_version": 1,
        "plan_id": "plan-denied",
        "task_id": "TASK-0021",
        "steps": [
            {
                "step_id": "denied",
                "adapter": "file_read",
                "operation": "read",
                "agent_role": "Researcher",
                "capability": "research",
                "required_permission": "modify_code",
            }
        ],
        "max_steps": 1,
    }

    response = client.post("/v1/executions/validate", headers=auth_headers, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DOMAIN_VALIDATION_FAILED"


def test_execution_inputs_and_free_form_transport_fields_are_rejected(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "schema_version": 1,
        "plan_id": "plan-private",
        "task_id": "TASK-0021",
        "steps": [
            {
                "step_id": "private",
                "adapter": "file_read",
                "operation": "read",
                "agent_role": "Researcher",
                "capability": "research",
                "required_permission": "read_control",
                "inputs": {"token": "must-not-cross-boundary"},
            }
        ],
        "max_steps": 1,
    }

    response = client.post("/v1/executions/validate", headers=auth_headers, json=payload)

    assert response.status_code == 422
    assert "must-not-cross-boundary" not in response.text


def test_noncanonical_capability_permission_pair_fails_closed(
    client: TestClient, auth_headers: dict[str, str]
) -> None:
    payload = {
        "schema_version": 1,
        "plan_id": "plan-mismatch",
        "task_id": "TASK-0021",
        "steps": [
            {
                "step_id": "mismatch",
                "adapter": "file_read",
                "operation": "read",
                "agent_role": "Controller",
                "capability": "plan",
                "required_permission": "coordinate",
            }
        ],
        "max_steps": 1,
    }

    response = client.post("/v1/executions/validate", headers=auth_headers, json=payload)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "DOMAIN_VALIDATION_FAILED"
