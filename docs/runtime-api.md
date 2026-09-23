# Governed Runtime API

The Runtime API is a private loopback service for authenticated read, validation and dry-run
operations. It does not dispatch workflows or executions and does not expose mutation endpoints.

## Install

```bash
python -m pip install -e ".[dev]"
```

## Configure a local credential

Generate a bearer token outside the repository and store only its SHA-256 digest in the server
environment. Do not commit either value.

```bash
export AIOS_API_TOKEN_SHA256="$(python -c 'import hashlib,getpass; print(hashlib.sha256(getpass.getpass("Token: ").encode()).hexdigest())')"
export AIOS_API_ROLE="Controller"
export AIOS_API_PRINCIPAL_ID="local-operator"
```

Keep the original token in an approved secret manager. The server receives only the verifier
digest.

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

Do not place the token in shell history in production. These commands illustrate the transport
contract only; use an approved credential-injection mechanism for operational deployment.

Interactive OpenAPI and ReDoc endpoints are disabled. Responses use versioned success and error
envelopes and carry `Cache-Control: no-store` plus a bounded request ID.
