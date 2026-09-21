"""Bounded cooperative background worker."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event
from typing import Protocol

from ai_os.agents import AgentRole, Permission

from .errors import SchedulerValidationError
from .models import DispatchRequest, SchedulerContext, WorkerLimits
from .service import SchedulerService


class DispatchGateway(Protocol):
    def dispatch(
        self,
        request: DispatchRequest,
        *,
        clock: Callable[[], datetime],
        cancelled: Callable[[], bool],
    ) -> bool: ...


class SchedulerWorker:
    def __init__(
        self,
        service: SchedulerService,
        gateway: DispatchGateway,
        *,
        worker_id: str,
        limits: WorkerLimits | None = None,
        stop_event: Event | None = None,
    ) -> None:
        limits = limits or WorkerLimits()
        if limits.schema_version != 1:
            raise SchedulerValidationError("unsupported worker limits schema")
        if not 1 <= limits.max_concurrency <= 32 or not 1 <= limits.max_batch <= 100:
            raise SchedulerValidationError("worker concurrency or batch limit is invalid")
        if not 0.1 <= limits.poll_seconds <= 60:
            raise SchedulerValidationError("worker poll interval is invalid")
        self.service = service
        self.gateway = gateway
        self.worker_id = worker_id
        self.limits = limits
        self.stop_event = stop_event or Event()
        self.context = SchedulerContext(AgentRole.CONTROLLER, Permission.COORDINATE)

    def stop(self) -> None:
        self.stop_event.set()

    def run_batch(self, *, clock: Callable[[], datetime] | None = None) -> int:
        now = clock or (lambda: datetime.now(UTC))
        requests: list[DispatchRequest] = []
        while len(requests) < self.limits.max_batch and not self.stop_event.is_set():
            request = self.service.claim(
                worker_id=self.worker_id,
                context=self.context,
                now=now(),
            )
            if request is None:
                break
            requests.append(request)
        if not requests:
            return 0
        with ThreadPoolExecutor(max_workers=self.limits.max_concurrency) as executor:
            futures = [
                executor.submit(self._dispatch_one, request, now)
                for request in requests
                if not self.stop_event.is_set()
            ]
            for future in futures:
                future.result()
        return len(futures)

    def _dispatch_one(self, request: DispatchRequest, clock: Callable[[], datetime]) -> None:
        if self.stop_event.is_set():
            return
        try:
            succeeded = self.gateway.dispatch(
                request, clock=clock, cancelled=self.stop_event.is_set
            )
        except Exception:
            succeeded = False
        self.service.complete(request, succeeded=succeeded, now=clock())
