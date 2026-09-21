"""Bounded cooperative background worker."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from threading import Event, Thread
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
        if not 1 <= limits.max_concurrency <= 32:
            raise SchedulerValidationError("worker concurrency limit is invalid")
        if not 0 <= limits.max_queue <= 100 or not 1 <= limits.max_batch <= 100:
            raise SchedulerValidationError("worker queue or batch limit is invalid")
        if not 0.1 <= limits.poll_seconds <= 60:
            raise SchedulerValidationError("worker poll interval is invalid")
        if not 5 <= limits.lease_seconds <= 300:
            raise SchedulerValidationError("worker lease duration is invalid")
        if not 0.1 <= limits.renewal_seconds < limits.lease_seconds:
            raise SchedulerValidationError("worker renewal interval is invalid")
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
        work: list[tuple[DispatchRequest, Event, Event, Thread]] = []
        capacity = min(
            self.limits.max_batch,
            self.limits.max_concurrency + self.limits.max_queue,
        )
        while len(work) < capacity and not self.stop_event.is_set():
            request = self.service.claim(
                worker_id=self.worker_id,
                context=self.context,
                now=now(),
                lease_seconds=self.limits.lease_seconds,
            )
            if request is None:
                break
            work.append((request, *self._start_heartbeat(request, now)))
        if not work:
            return 0
        if self.stop_event.is_set():
            for request, heartbeat_stop, _, heartbeat in work:
                heartbeat_stop.set()
                heartbeat.join()
                self.service.release(request, context=self.context, now=now())
            return 0
        with ThreadPoolExecutor(max_workers=self.limits.max_concurrency) as executor:
            futures = [
                executor.submit(
                    self._dispatch_one,
                    request,
                    now,
                    heartbeat_stop,
                    lease_lost,
                    heartbeat,
                )
                for request, heartbeat_stop, lease_lost, heartbeat in work
            ]
            for future in futures:
                future.result()
        return len(futures)

    def _start_heartbeat(
        self,
        request: DispatchRequest,
        clock: Callable[[], datetime],
    ) -> tuple[Event, Event, Thread]:
        heartbeat_stop = Event()
        lease_lost = Event()
        heartbeat = Thread(
            target=self._renew_lease,
            args=(request, clock, heartbeat_stop, lease_lost),
            daemon=True,
        )
        heartbeat.start()
        return heartbeat_stop, lease_lost, heartbeat

    def _dispatch_one(
        self,
        request: DispatchRequest,
        clock: Callable[[], datetime],
        heartbeat_stop: Event,
        lease_lost: Event,
        heartbeat: Thread,
    ) -> None:
        if lease_lost.is_set():
            heartbeat_stop.set()
            heartbeat.join()
            return
        if self.stop_event.is_set():
            heartbeat_stop.set()
            heartbeat.join()
            self.service.release(request, context=self.context, now=clock())
            return
        try:
            succeeded = self.gateway.dispatch(
                request,
                clock=clock,
                cancelled=lambda: self.stop_event.is_set() or lease_lost.is_set(),
            )
        except Exception:
            succeeded = False
        finally:
            heartbeat_stop.set()
            heartbeat.join()
        if lease_lost.is_set():
            return
        self.service.complete(
            request,
            succeeded=succeeded and not self.stop_event.is_set(),
            now=clock(),
        )

    def _renew_lease(
        self,
        request: DispatchRequest,
        clock: Callable[[], datetime],
        heartbeat_stop: Event,
        lease_lost: Event,
    ) -> None:
        while not heartbeat_stop.wait(self.limits.renewal_seconds):
            if self.stop_event.is_set():
                return
            try:
                self.service.renew(
                    request,
                    context=self.context,
                    now=clock(),
                    lease_seconds=self.limits.lease_seconds,
                )
            except Exception:
                lease_lost.set()
                return
