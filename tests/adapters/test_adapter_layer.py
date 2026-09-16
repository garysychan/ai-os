"""Adapter Layer Core policy, registry, audit and file safety tests."""

from __future__ import annotations

import unittest
from dataclasses import FrozenInstanceError, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

from ai_os.adapters import (
    AdapterInvocation,
    AdapterMetadata,
    AdapterPolicyError,
    AdapterRegistry,
    AdapterRegistryError,
    AdapterResult,
    AdapterRisk,
    AdapterService,
    AdapterStatus,
    AdapterValidationError,
    ReadOnlyFileAdapter,
    SideEffect,
    make_audit_event,
    redact_pairs,
    redact_text,
    validate_invocation,
    validate_metadata,
    validate_result,
)
from ai_os.agents import AgentRole, Capability, Permission
from ai_os.tasks import AcceptanceCriterion, Priority, Task, TaskStatus

NOW = datetime(2026, 9, 16, tzinfo=UTC)


def task(status: TaskStatus = TaskStatus.IN_PROGRESS) -> Task:
    return Task(
        task_id="TASK-0012",
        title="Adapter Layer",
        priority=Priority.P1,
        status=status,
        agents=("Developer",),
        dependencies=("TASK-0011",),
        acceptance_criteria=(AcceptanceCriterion("safe adapters"),),
    )


def invocation(path: Path) -> AdapterInvocation:
    return AdapterInvocation(
        invocation_id="invoke-1",
        task_id="TASK-0012",
        adapter="file-read",
        version="1",
        operation="read_text",
        agent_role=AgentRole.DEVELOPER,
        capability=Capability.IMPLEMENT,
        required_permission=Permission.MODIFY_CODE,
        inputs=(("path", str(path)), ("token", "must-not-leak")),
        deadline=NOW + timedelta(seconds=5),
    )


class AdapterLayerTests(unittest.TestCase):
    def test_read_only_file_adapter_executes_with_redacted_immutable_audit(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "input.txt"
            target.write_text("governed", encoding="utf-8")
            service = AdapterService(
                AdapterRegistry((ReadOnlyFileAdapter((root,)),)), max_output_bytes=1000
            )

            result, audit = service.execute(task(), invocation(target), clock=lambda: NOW)

            self.assertEqual(result.status, AdapterStatus.SUCCESS)
            self.assertEqual(dict(result.outputs)["content"], "governed")
            self.assertIn("token=[REDACTED]", audit.evidence)
            self.assertNotIn("must-not-leak", " ".join(audit.evidence))
            with self.assertRaises(FrozenInstanceError):
                audit.sequence = 2  # type: ignore[misc]

    def test_registry_is_versioned_explicit_and_default_deny(self) -> None:
        with TemporaryDirectory() as directory:
            adapter = ReadOnlyFileAdapter((Path(directory),))
            registry = AdapterRegistry((adapter,))
            self.assertIs(registry.resolve("file-read", "1", "read_text"), adapter)
            with self.assertRaisesRegex(AdapterRegistryError, "unknown adapter"):
                registry.resolve("file-read", "2", "read_text")
            with self.assertRaisesRegex(AdapterRegistryError, "unsupported operation"):
                registry.resolve("file-read", "1", "write_text")
            with self.assertRaisesRegex(AdapterRegistryError, "duplicate"):
                registry.register(adapter)

    def test_policy_denies_status_assignment_permission_and_write_side_effect(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "input.txt"
            target.write_text("safe", encoding="utf-8")
            service = AdapterService(AdapterRegistry((ReadOnlyFileAdapter((root,)),)))
            with self.assertRaisesRegex(AdapterPolicyError, "IN_PROGRESS"):
                service.execute(task(TaskStatus.REVIEW), invocation(target), clock=lambda: NOW)
            with self.assertRaisesRegex(AdapterPolicyError, "requires modify_code"):
                service.execute(
                    task(),
                    replace(invocation(target), required_permission=Permission.READ_CONTROL),
                    clock=lambda: NOW,
                )
            with self.assertRaisesRegex(AdapterPolicyError, "not assigned"):
                service.execute(
                    task(),
                    replace(invocation(target), agent_role=AgentRole.RESEARCHER),
                    clock=lambda: NOW,
                )

            metadata = replace(
                ReadOnlyFileAdapter((root,)).metadata,
                side_effect=SideEffect.WRITE_EXTERNAL,
            )

            class WriteAdapter:
                def __init__(self) -> None:
                    self.metadata = metadata

                def invoke(self, item: AdapterInvocation) -> AdapterResult:
                    return AdapterResult(item.invocation_id, AdapterStatus.SUCCESS, "unsafe")

            denied = AdapterService(AdapterRegistry((WriteAdapter(),)))
            with self.assertRaisesRegex(AdapterPolicyError, "write-capable"):
                denied.execute(task(), invocation(target), clock=lambda: NOW)

    def test_file_adapter_blocks_escape_symlink_sensitive_and_oversize(self) -> None:
        with TemporaryDirectory() as approved, TemporaryDirectory() as outside:
            root = Path(approved)
            external = Path(outside) / "external.txt"
            external.write_text("outside", encoding="utf-8")
            adapter = ReadOnlyFileAdapter((root,), max_bytes=4)
            service = AdapterService(AdapterRegistry((adapter,)))
            with self.assertRaisesRegex(AdapterPolicyError, "escapes approved roots"):
                service.execute(task(), invocation(external), clock=lambda: NOW)

            link = root / "link.txt"
            link.symlink_to(external)
            with self.assertRaisesRegex(AdapterPolicyError, "escapes approved roots"):
                service.execute(task(), invocation(link), clock=lambda: NOW)

            secret = root / ".env"
            secret.write_text("x", encoding="utf-8")
            with self.assertRaisesRegex(AdapterPolicyError, "sensitive"):
                service.execute(task(), invocation(secret), clock=lambda: NOW)

            large = root / "large.txt"
            large.write_text("12345", encoding="utf-8")
            with self.assertRaisesRegex(AdapterPolicyError, "size limit"):
                service.execute(task(), invocation(large), clock=lambda: NOW)

    def test_validation_rejects_expired_duplicate_and_unbounded_results(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "input.txt"
            path.write_text("safe", encoding="utf-8")
            item = invocation(path)
            with self.assertRaisesRegex(AdapterValidationError, "expired"):
                validate_invocation(replace(item, deadline=NOW), NOW)
            with self.assertRaisesRegex(AdapterValidationError, "unique"):
                validate_invocation(replace(item, inputs=(("path", "a"), ("path", "b"))), NOW)
            with self.assertRaisesRegex(AdapterValidationError, "output limit"):
                validate_result(
                    AdapterResult(item.invocation_id, AdapterStatus.SUCCESS, "x", (("x", "123"),)),
                    item,
                    2,
                )
            with self.assertRaisesRegex(AdapterValidationError, "declared operations"):
                validate_metadata(
                    AdapterMetadata(
                        "x",
                        "1",
                        frozenset({"read"}),
                        AdapterRisk.LOW,
                        SideEffect.NONE,
                        frozenset({"write"}),
                    )
                )

    def test_redaction_is_case_insensitive_and_preserves_safe_values(self) -> None:
        self.assertEqual(
            redact_pairs((("Authorization", "Bearer x"), ("path", "/safe"))),
            (("Authorization", "[REDACTED]"), ("path", "/safe")),
        )
        self.assertEqual(
            redact_text("request failed token=abc123 password:open"),
            "request failed token=[REDACTED] password=[REDACTED]",
        )

    def test_cancellation_is_audited_without_invoking_adapter(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "input.txt"
            target.write_text("safe", encoding="utf-8")
            service = AdapterService(AdapterRegistry((ReadOnlyFileAdapter((root,)),)))
            result, audit = service.execute(
                task(), invocation(target), clock=lambda: NOW, cancelled=lambda: True
            )
            self.assertEqual(result.status, AdapterStatus.CANCELLED)
            self.assertEqual(audit.status, AdapterStatus.CANCELLED)
            self.assertEqual(audit.evidence[-1], "cancelled=true")

    def test_retry_budget_requires_idempotent_operation(self) -> None:
        with TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "input.txt"
            target.write_text("safe", encoding="utf-8")
            service = AdapterService(AdapterRegistry((ReadOnlyFileAdapter((root,)),)))
            result, _ = service.execute(
                task(), replace(invocation(target), attempt=2, max_attempts=2), clock=lambda: NOW
            )
            self.assertEqual(result.status, AdapterStatus.SUCCESS)

            class NonIdempotentAdapter:
                metadata = replace(
                    ReadOnlyFileAdapter((root,)).metadata,
                    idempotent_operations=frozenset(),
                )

                def invoke(self, item: AdapterInvocation) -> AdapterResult:
                    return AdapterResult(item.invocation_id, AdapterStatus.SUCCESS, "unsafe")

            denied = AdapterService(AdapterRegistry((NonIdempotentAdapter(),)))
            with self.assertRaisesRegex(AdapterPolicyError, "non-idempotent"):
                denied.execute(
                    task(),
                    replace(invocation(target), attempt=2, max_attempts=2),
                    clock=lambda: NOW,
                )

    def test_result_evidence_and_errors_are_redacted_in_audit(self) -> None:
        item = replace(invocation(Path("/tmp/input")), inputs=())
        result = AdapterResult(
            item.invocation_id,
            AdapterStatus.FAILED,
            "failed",
            evidence=("token=abc123",),
            errors=("password:open",),
        )
        audit = make_audit_event(1, item, result, NOW)
        self.assertEqual(
            audit.evidence,
            ("token=[REDACTED]", "error=password=[REDACTED]"),
        )


if __name__ == "__main__":
    unittest.main()
