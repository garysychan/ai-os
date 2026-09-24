# Governed Runtime API

The Runtime API is a private loopback service for authenticated read, validation and dry-run
operations. It does not dispatch workflows or executions and does not expose mutation endpoints.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Configure authentication

Production resolves bearer material through the governed `SecretService`. Configure only a
canonical environment-backed reference; never put token material or a digest in source,
documentation, logs, audit evidence or exceptions.

```bash
export AIOS_API_TOKEN_REF="env://AIOS_API_TOKEN"
export AIOS_API_ROLE="Controller"
export AIOS_API_PRINCIPAL_ID="local-operator"
```

The resolved production token must contain at least 32 bytes. Missing, weak or unresolved
material rejects startup. Development and test may use synthetic fixtures, but production must
use the secret reference path.

## Run

```bash
aios-api --root . --environment development --port 8765
```

The server binds to `127.0.0.1`. Non-loopback bindings fail closed.

## Query

```bash
curl -H "Authorization: Bearer $AIOS_API_TOKEN" http://127.0.0.1:8765/v1/version
curl -H "Authorization: Bearer $AIOS_API_TOKEN" http://127.0.0.1:8765/v1/tasks
curl -H "Authorization: Bearer $AIOS_API_TOKEN" http://127.0.0.1:8765/v1/workflows
```

Use an approved credential-injection mechanism for operational deployment. The request body limit
is enforced while ASGI chunks are received, including requests with a missing or falsified
`Content-Length`; exceeding it returns bounded HTTP 413 evidence.

Execution inspection returns an explicit allowlist containing identifiers, governed status, safe
timestamps and bounded counts only. Inputs, outputs, evidence, tool data, credentials, secret
references, environment variables and exception text are never projected.

Health is fail-closed: missing monitoring evidence is `UNKNOWN` in development/test and
`UNAVAILABLE` in production. The production composition root initializes the governed SQLite
store, workflow registry, observability/audit, metrics, health monitoring, runtime configuration,
authentication and authorization services before serving inspection routes.

Security-relevant API events are persisted through the runtime observability store with bounded
allowlisted fields such as request ID, stable principal ID, role, method, route template, status,
outcome and duration. Raw URLs, headers, bodies, query payloads, tokens and private runtime data
are excluded.

Interactive OpenAPI and ReDoc endpoints are disabled. Responses use versioned success and error
envelopes and carry `Cache-Control: no-store` plus a bounded request ID.
