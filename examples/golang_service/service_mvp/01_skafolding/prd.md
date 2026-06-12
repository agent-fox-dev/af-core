## Background

This is a greenfield project — no prior scaffold or template exists for Go services in this repository. The motivation is simply to establish a minimal, working Go service as a starting point ("get the ball rolling") for future development. No existing service is being replaced or migrated.

---

## Intent

Provide a minimal, runnable Go service using the Echo framework that serves as a clean starting point for further development. This is a standalone starter service, not a reusable template library.

---

## Goals

- Expose a `/ping` endpoint that returns a simple, successful response.
- Expose `/healthz` and `/readyz` endpoints compatible with Kubernetes liveness and readiness probes.
- Use the Echo framework with a standard middleware stack (Logger, Recovery, CORS).
- Follow idiomatic Go project layout (`cmd/`, `internal/`, and root-level reusable packages).
- Use Go module path `github.com/agent-fox-dev/srv-skafolding` targeting Go 1.25+.
- Keep the codebase as simple as possible — no unnecessary abstractions or dependencies.

---

## Non-Goals

- No business logic beyond the `/ping` endpoint.
- No authentication or authorisation.
- No database integration.
- No configuration management or environment variable parsing.
- No deployment manifests (Kubernetes YAML, Helm charts, etc.).
- No metrics or observability endpoints (e.g., `/metrics`).
- No rate limiting or advanced security middleware beyond CORS.
- This is not intended to be a reusable template library consumed by other projects.

---

## Endpoints

| Method | Path       | Description                                      | Kubernetes Probe |
|--------|------------|--------------------------------------------------|------------------|
| GET    | `/ping`    | Returns a simple pong response (e.g., `{"message":"pong"}`). | — |
| GET    | `/healthz` | Liveness probe — confirms the process is alive. Returns `200 OK`. | Liveness |
| GET    | `/readyz`  | Readiness probe — confirms the service is ready to accept traffic. Returns `200 OK`. | Readiness |

---

## Middleware Stack

The Echo instance must be configured with the following middleware, applied globally in this order:

1. **Logger** (`echo/middleware.Logger`) — structured request/response logging.
2. **Recovery** (`echo/middleware.Recover`) — catches panics and returns a `500` response to prevent process crashes.
3. **CORS** (`echo/middleware.CORS`) — enables cross-origin resource sharing with Echo's default CORS configuration.

No additional middleware (e.g., rate limiting, Helmet, JWT) is in scope.

---

## Project Layout

The repository must follow standard Go project conventions:

```
srv-skafolding/
├── cmd/
│   └── server/
│       └── main.go          # Entry point — wires up Echo, middleware, routes, and starts the HTTP server.
├── internal/
│   └── handler/
│       └── handler.go       # Internal HTTP handler implementations (ping, healthz, readyz).
├── go.mod                   # Module: github.com/agent-fox-dev/srv-skafolding, Go 1.25+
├── go.sum
└── README.md
```

- `cmd/` contains only entry points (i.e., `main` packages).
- `internal/` contains all code that is private to this service and must not be imported by external projects.
- Any code intended to be reusable by other projects in future (e.g., an `api/` or `auth/` package) would live in dedicated root-level folders. No such packages are in scope for this initial scaffold.

---

## Technical Specification

- **Language:** Go 1.25+
- **Module path:** `github.com/agent-fox-dev/srv-skafolding`
- **Framework:** [Echo](https://echo.labstack.com/) (latest stable v4)
- **Middleware:** Logger, Recovery, CORS (Echo built-ins only)
- **Configuration:** None — no environment variable parsing or config struct. The HTTP server may use a hardcoded default address (e.g., `:8080`).
- **Dependencies:** Minimal — only Echo and its standard library dependencies.

---

## Acceptance Criteria

1. `go build ./...` succeeds with no errors.
2. Running `cmd/server/main.go` starts an HTTP server.
3. `GET /ping` returns `200 OK` with a JSON body (e.g., `{"message":"pong"}`).
4. `GET /healthz` returns `200 OK`.
5. `GET /readyz` returns `200 OK`.
6. Logger, Recovery, and CORS middleware are active for all routes.
7. A panic in a handler does not crash the process (Recovery middleware catches it).
8. The project structure matches the layout defined above.
