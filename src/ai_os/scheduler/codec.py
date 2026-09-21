"""Strict JSON codec for Scheduler records."""

from __future__ import annotations

import json
from datetime import datetime

from .models import JobRecord, JobSpec, JobState, ScheduleKind
from .validation import validate_spec


def dump_job(record: JobRecord) -> str:
    spec = record.spec
    return json.dumps(
        {
            "schema_version": record.schema_version,
            "spec": {
                "job_id": spec.job_id,
                "task_id": spec.task_id,
                "workflow_name": spec.workflow_name,
                "workflow_version": spec.workflow_version,
                "run_at": spec.run_at.isoformat(),
                "kind": spec.kind.value,
                "interval_seconds": spec.interval_seconds,
                "max_attempts": spec.max_attempts,
                "retry_backoff_seconds": spec.retry_backoff_seconds,
                "timeout_seconds": spec.timeout_seconds,
                "schema_version": spec.schema_version,
            },
            "state": record.state.value,
            "attempts": record.attempts,
            "next_run_at": record.next_run_at.isoformat(),
            "created_at": record.created_at.isoformat(),
            "updated_at": record.updated_at.isoformat(),
            "lease_owner": record.lease_owner,
            "lease_token": record.lease_token,
            "lease_expires_at": (
                record.lease_expires_at.isoformat() if record.lease_expires_at else None
            ),
            "last_error": record.last_error,
        },
        sort_keys=True,
        separators=(",", ":"),
    )


def load_job(payload: str) -> JobRecord:
    data = json.loads(payload)
    raw = data["spec"]
    spec = validate_spec(
        JobSpec(
            job_id=raw["job_id"],
            task_id=raw["task_id"],
            workflow_name=raw["workflow_name"],
            workflow_version=raw["workflow_version"],
            run_at=datetime.fromisoformat(raw["run_at"]),
            kind=ScheduleKind(raw["kind"]),
            interval_seconds=raw["interval_seconds"],
            max_attempts=raw["max_attempts"],
            retry_backoff_seconds=raw["retry_backoff_seconds"],
            timeout_seconds=raw["timeout_seconds"],
            schema_version=raw["schema_version"],
        )
    )
    lease_expires = data["lease_expires_at"]
    return JobRecord(
        spec=spec,
        state=JobState(data["state"]),
        attempts=data["attempts"],
        next_run_at=datetime.fromisoformat(data["next_run_at"]),
        created_at=datetime.fromisoformat(data["created_at"]),
        updated_at=datetime.fromisoformat(data["updated_at"]),
        lease_owner=data["lease_owner"],
        lease_token=data["lease_token"],
        lease_expires_at=datetime.fromisoformat(lease_expires) if lease_expires else None,
        last_error=data["last_error"],
        schema_version=data["schema_version"],
    )
