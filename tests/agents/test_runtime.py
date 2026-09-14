import unittest

from ai_os.agents import (
    AgentRegistry, AgentRole, AgentRouter, AgentRuntime, Capability,
    ExecutionPreconditionError, ExecutionRequest, ExecutionStatus,
    PermissionDeniedError, canonical_agents,
)
from ai_os.tasks import (
    AcceptanceCriterion, Priority, ReviewResult, Task, TaskStatus,
)


def make_task(
    status: TaskStatus = TaskStatus.IN_PROGRESS,
    dependencies: tuple[str, ...] = (),
    agents: tuple[str, ...] = ("Developer",),
) -> Task:
    return Task(
        "TASK-0101", "Runtime task", Priority.P1, status,
        agents, dependencies, (AcceptanceCriterion("complete"),),
        ("previous completion evidence",) if status is TaskStatus.DONE else (),
    )


class RuntimeTests(unittest.TestCase):
    def setUp(self) -> None:
        registry = AgentRegistry(canonical_agents())
        self.runtime = AgentRuntime(AgentRouter(registry))

    def test_dispatch_returns_immutable_handoff_without_mutating_task(self) -> None:
        task = make_task()
        result = self.runtime.execute(ExecutionRequest(
            task=task, capability=Capability.IMPLEMENT,
            objective="Implement runtime", actor="Codex",
            requested_role=AgentRole.DEVELOPER, evidence=("CR-2026-006",),
        ))
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertEqual(result.handoff.task_id, task.task_id)
        self.assertEqual(task.status, TaskStatus.IN_PROGRESS)

    def test_unfinished_dependency_blocks_execution(self) -> None:
        request = ExecutionRequest(
            task=make_task(dependencies=("TASK-0003",)),
            capability=Capability.IMPLEMENT,
            objective="Implement", actor="Codex",
        )
        with self.assertRaises(ExecutionPreconditionError):
            self.runtime.execute(
                request, dependency_states={"TASK-0003": TaskStatus.REVIEW}
            )

    def test_todo_and_done_are_not_executable(self) -> None:
        for status in (TaskStatus.TODO, TaskStatus.DONE):
            with self.assertRaises(ExecutionPreconditionError):
                self.runtime.execute(ExecutionRequest(
                    task=make_task(status), capability=Capability.IMPLEMENT,
                    objective="Implement", actor="Codex",
                ))

    def test_developer_cannot_complete_task(self) -> None:
        with self.assertRaises(PermissionDeniedError):
            self.runtime.execute(ExecutionRequest(
                task=make_task(), capability=Capability.IMPLEMENT,
                objective="Complete", actor="Codex",
                requested_role=AgentRole.DEVELOPER,
                target_status=TaskStatus.DONE,
            ))

    def test_controller_completion_requires_approved_review(self) -> None:
        request = ExecutionRequest(
            task=make_task(TaskStatus.REVIEW),
            capability=Capability.GOVERN,
            objective="Complete governed task",
            actor="Controller",
            requested_role=AgentRole.CONTROLLER,
            target_status=TaskStatus.DONE,
            review_result=ReviewResult.APPROVE,
        )
        result = self.runtime.execute(request)
        self.assertEqual(result.status, ExecutionStatus.SUCCESS)
        self.assertIsNone(result.review_result)

    def test_unassigned_role_cannot_execute_task(self) -> None:
        with self.assertRaises(ExecutionPreconditionError):
            self.runtime.execute(ExecutionRequest(
                task=make_task(agents=("Tester",)),
                capability=Capability.IMPLEMENT,
                objective="Implement", actor="Developer",
                requested_role=AgentRole.DEVELOPER,
            ))

    def test_role_cannot_run_in_unsupported_task_state(self) -> None:
        with self.assertRaises(ExecutionPreconditionError):
            self.runtime.execute(ExecutionRequest(
                task=make_task(TaskStatus.REVIEW),
                capability=Capability.IMPLEMENT,
                objective="Implement during review", actor="Developer",
                requested_role=AgentRole.DEVELOPER,
            ))

    def test_review_requires_review_state_and_preserves_result(self) -> None:
        request = ExecutionRequest(
            task=make_task(TaskStatus.REVIEW, agents=("Reviewer",)),
            capability=Capability.REVIEW,
            objective="Review", actor="Reviewer",
            requested_role=AgentRole.REVIEWER,
            review_result=ReviewResult.APPROVE,
        )
        result = self.runtime.execute(request)
        self.assertEqual(result.review_result, ReviewResult.APPROVE)

    def test_non_reviewer_cannot_emit_review_result(self) -> None:
        with self.assertRaises(PermissionDeniedError):
            self.runtime.execute(ExecutionRequest(
                task=make_task(), capability=Capability.IMPLEMENT,
                objective="Implement", actor="Developer",
                review_result=ReviewResult.APPROVE,
            ))


if __name__ == "__main__":
    unittest.main()
