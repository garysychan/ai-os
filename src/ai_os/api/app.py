"""FastAPI application factory for the governed Runtime boundary."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from time import monotonic
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from ai_os.agents import AgentRole, Permission, PermissionPolicy

from .audit import ApiAuditRecorder
from .auth import Principal, StaticBearerAuthenticator
from .config import ApiConfig
from .errors import ApiError
from .models import ErrorDetail, ErrorEnvelope, ExecutionPlanInput, ResponseEnvelope, WorkflowInput
from .services import RuntimeApiServices

Handler = Callable[[Request], Awaitable[JSONResponse]]


def create_app(
    config: ApiConfig,
    authenticator: StaticBearerAuthenticator,
    *,
    services: RuntimeApiServices | None = None,
) -> FastAPI:
    runtime = services or RuntimeApiServices(config)
    app = FastAPI(title="AI OS Governed Runtime API", version="1", docs_url=None, redoc_url=None)
    app.state.config = config
    app.state.authenticator = authenticator
    app.state.services = runtime
    app.state.audit = ApiAuditRecorder(config.max_audit_events, runtime.observability)

    @app.middleware("http")
    async def request_boundary(request: Request, call_next: Handler) -> JSONResponse:
        started = monotonic()
        request.state.request_id = f"req-{uuid4().hex}"
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                too_large = int(content_length) > config.max_request_bytes
            except ValueError:
                too_large = True
            if too_large:
                response = _error(
                    request, 413, "REQUEST_TOO_LARGE", "request exceeds configured bound"
                )
                _record_audit(request, response, app.state.audit, started)
                return response
        if request.method in {"POST", "PUT", "PATCH"}:
            body = await _receive_bounded_body(request, config.max_request_bytes)
            if body is None:
                response = _error(
                    request, 413, "REQUEST_TOO_LARGE", "request exceeds configured bound"
                )
                _record_audit(request, response, app.state.audit, started)
                return response
            request._body = body
        try:
            async with asyncio.timeout(config.request_timeout_seconds):
                response = await call_next(request)
        except TimeoutError:
            response = _error(
                request, 504, "REQUEST_TIMED_OUT", "request exceeded configured timeout"
            )
            _record_audit(request, response, app.state.audit, started)
            return response
        response.headers["X-Request-ID"] = request.state.request_id
        response.headers["Cache-Control"] = "no-store"
        _record_audit(request, response, app.state.audit, started)
        return response

    @app.exception_handler(ApiError)
    async def api_error(request: Request, error: ApiError) -> JSONResponse:
        return _error(request, error.status_code, error.code, error.message)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        del error
        return _error(request, 422, "VALIDATION_FAILED", "request validation failed")

    @app.exception_handler(Exception)
    async def internal_error(request: Request, error: Exception) -> JSONResponse:
        del error
        return _error(request, 500, "INTERNAL_ERROR", "internal request failure")

    def principal(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> Principal:
        if authorization is None or not authorization.startswith("Bearer "):
            raise ApiError(
                401,
                "AUTHENTICATION_REQUIRED",
                "valid bearer authentication is required",
            )
        token = authorization[7:]
        try:
            identity = authenticator.authenticate(token)
        except ValueError as error:
            raise ApiError(401, "AUTHENTICATION_FAILED", "bearer credential is invalid") from error
        if identity is None:
            raise ApiError(401, "AUTHENTICATION_FAILED", "bearer credential is invalid")
        request.state.agent_role = identity.role.value
        request.state.principal_id = identity.principal_id
        return identity

    def authorize(permission: Permission) -> Callable[[Principal], Principal]:
        def dependency(identity: Principal = Depends(principal)) -> Principal:
            if not PermissionPolicy().allows(identity.role, permission):
                raise ApiError(403, "AUTHORIZATION_DENIED", "request is not authorized")
            return identity

        return dependency

    read = authorize(Permission.READ_CONTROL)
    propose = authorize(Permission.PROPOSE_CHANGE)

    @app.get("/v1/version")
    def get_version(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _success(request, runtime.version())

    @app.get("/v1/capabilities")
    def get_capabilities(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _success(request, runtime.capabilities())

    @app.get("/v1/health")
    def get_health(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        return _success(request, runtime.health(identity.role))

    @app.get("/v1/control-plane/status")
    def control_status(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _call(request, runtime.control_plane)

    @app.post("/v1/control-plane/check")
    def control_check(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _call(request, runtime.check_control_plane)

    @app.get("/v1/tasks")
    def tasks(
        request: Request,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1),
        identity: Principal = Depends(read),
    ) -> JSONResponse:
        del identity
        if limit > config.max_page_size:
            raise ApiError(422, "QUERY_BOUND_EXCEEDED", "page size exceeds configured bound")
        try:
            data, total = runtime.tasks(offset=offset, limit=limit)
        except Exception as error:
            raise _domain_error(error) from error
        return _success(request, data, {"offset": offset, "limit": limit, "total": total})

    @app.get("/v1/tasks/transitions")
    def transitions(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _call(request, runtime.transitions)

    @app.get("/v1/tasks/{task_id}")
    def task(request: Request, task_id: str, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.task(task_id))

    @app.get("/v1/agents")
    def agents(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _success(request, runtime.agents())

    @app.get("/v1/agents/{role}")
    def agent(
        request: Request,
        role: AgentRole,
        identity: Principal = Depends(read),
    ) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.agent(role))

    @app.get("/v1/workflows")
    def workflows(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        del identity
        return _success(request, runtime.workflows())

    @app.get("/v1/workflows/{name}/{workflow_version}")
    def workflow(
        request: Request,
        name: str,
        workflow_version: str,
        identity: Principal = Depends(read),
    ) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.workflow(name, workflow_version))

    @app.post("/v1/workflows/validate")
    def workflow_validate(
        request: Request, payload: WorkflowInput, identity: Principal = Depends(read)
    ) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.validate_workflow(payload))

    @app.post("/v1/workflows/dry-run")
    def workflow_dry_run(
        request: Request, payload: WorkflowInput, identity: Principal = Depends(propose)
    ) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.dry_run_workflow(payload))

    @app.post("/v1/executions/validate")
    def execution_validate(
        request: Request, payload: ExecutionPlanInput, identity: Principal = Depends(read)
    ) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.validate_execution(payload))

    @app.post("/v1/executions/dry-run")
    def execution_dry_run(
        request: Request, payload: ExecutionPlanInput, identity: Principal = Depends(propose)
    ) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.dry_run_execution(payload))

    @app.get("/v1/executions/{execution_id}")
    def execution(
        request: Request, execution_id: str, identity: Principal = Depends(read)
    ) -> JSONResponse:
        del identity
        return _call(request, lambda: runtime.execution(execution_id))

    @app.get("/v1/executions/{execution_id}/trace")
    def execution_trace(
        request: Request,
        execution_id: str,
        limit: int = Query(default=100, ge=1),
        identity: Principal = Depends(read),
    ) -> JSONResponse:
        if limit > config.max_page_size:
            raise ApiError(422, "QUERY_BOUND_EXCEEDED", "page size exceeds configured bound")
        return _call(
            request,
            lambda: runtime.audit(identity.role, limit=limit, trace_id=execution_id),
        )

    @app.get("/v1/audit")
    def audit(
        request: Request,
        limit: int = Query(default=100, ge=1),
        trace_id: str | None = None,
        identity: Principal = Depends(read),
    ) -> JSONResponse:
        if limit > config.max_page_size:
            raise ApiError(422, "QUERY_BOUND_EXCEEDED", "page size exceeds configured bound")
        return _call(request, lambda: runtime.audit(identity.role, limit=limit, trace_id=trace_id))

    @app.get("/v1/metrics")
    def metrics(request: Request, identity: Principal = Depends(read)) -> JSONResponse:
        return _call(request, lambda: runtime.metrics(identity.role))

    return app


def _success(request: Request, data: object, meta: dict[str, object] | None = None) -> JSONResponse:
    payload = ResponseEnvelope(request_id=request.state.request_id, data=data, meta=meta or {})
    return JSONResponse(payload.model_dump(mode="json"))


def _error(request: Request, status: int, code: str, message: str) -> JSONResponse:
    payload = ErrorEnvelope(
        request_id=getattr(request.state, "request_id", "req-unavailable"),
        error=ErrorDetail(code=code, message=message),
    )
    return JSONResponse(payload.model_dump(mode="json"), status_code=status)


def _call(request: Request, operation: Callable[[], object]) -> JSONResponse:
    try:
        return _success(request, operation())
    except Exception as error:
        raise _domain_error(error) from error


def _domain_error(error: Exception) -> ApiError:
    if isinstance(error, KeyError):
        return ApiError(404, "RESOURCE_NOT_FOUND", "governed resource was not found")
    if isinstance(error, (ValueError, TypeError)):
        return ApiError(422, "DOMAIN_VALIDATION_FAILED", "domain validation failed")
    return ApiError(500, "RUNTIME_FAILURE", "governed runtime request failed")


def _record_audit(
    request: Request,
    response: JSONResponse,
    recorder: ApiAuditRecorder,
    started: float,
) -> None:
    route = request.scope.get("route")
    route_path = getattr(route, "path", "/unmatched")
    recorder.record(
        request_id=request.state.request_id,
        method=request.method,
        route=route_path,
        status_code=response.status_code,
        duration_ms=int(max(0, (monotonic() - started) * 1000)),
        principal_id=getattr(request.state, "principal_id", None),
        agent_role=getattr(request.state, "agent_role", None),
    )


async def _receive_bounded_body(request: Request, maximum: int) -> bytes | None:
    chunks: list[bytes] = []
    received = 0
    while True:
        message = await request.receive()
        if message["type"] == "http.disconnect":
            return b""
        chunk = message.get("body", b"")
        received += len(chunk)
        if received > maximum:
            return None
        chunks.append(chunk)
        if not message.get("more_body", False):
            return b"".join(chunks)
