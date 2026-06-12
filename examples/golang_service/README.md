spec init --name "service mvp" service_mvp

spec -C service_mvp new --name "skafolding" prd.md

spec -C service_mvp assess 01_skafolding

````
Quality: needs_refinement
Summary: The PRD for "Skafolding" describes a Go service scaffold using the Echo framework with a ping endpoint and Kubernetes-compatible health/uptime endpoints. The core intent is reasonably clear, but the document is essentially a single loosely structured paragraph — it lacks formal sections for Goals, Non-Goals, and Background. Additionally, several implementation details are ambiguous or missing (e.g., exact Kubernetes probe endpoints, security middleware specifics, and deployment context). The PRD can proceed after a few targeted clarifications.

Gaps:
  1. No formal 'Goals' section with measurable outcomes (e.g., response time targets, availability SLOs, test coverage expectations).
  2. No 'Non-Goals' section — scope boundaries are entirely absent, leaving it unclear what is intentionally excluded (e.g., authentication, database integration, deployment manifests).
  3. No 'Background' section — there is no context about why this scaffold is being created, what problem it solves, or what prior art or existing services informed the design.
  4. The 'Intent' is implicit rather than explicitly stated; it is inferable but not formally articulated.
  5. 'Typical health and uptime monitoring endpoints' is vague — specific routes (e.g., /healthz, /readyz, /livez, /metrics) are not enumerated.
  6. The Echo framework 'typical handlers for logging, error handling and security' are not specified — it is unclear which middleware stack is expected (e.g., zerolog, recover, CORS, Helmet, rate-limiting).
  7. Owner field is empty — no accountable party is identified for this spec.
  8. 'Reusable code in dedicated root folders' is mentioned with examples but no concrete packages are defined for this service.
  9. No mention of Go version, module path/name, or any configuration management approach (env vars, config files, etc.).

Questions:
  q1: What is the explicit, one-sentence intent of this scaffold? Is the goal to provide a reusable starting template for all future Go services, or is this a specific standalone service?
  q2: Which specific Kubernetes health/uptime endpoints should the service expose?
  q3: Which Echo middleware should be included in the default middleware stack?
  q4: What are the explicit Non-Goals for this scaffold? What should it deliberately NOT include?
  q5: What is the background or motivation for creating this scaffold? Is there an existing service or template it replaces, or is this greenfield?
  q6: What Go module path and Go version should be used for this service?
  q7: Should the scaffold include configuration management (e.g., environment variable parsing, a config struct)? If so, which library, if any, is preferred?
```

spec -C service_mvp refine 01_skafolding > questions.json

spec -C service_mvp refine 01_skafolding --answers answers.json

spec -C service_mvp accept 01_skafolding

spec -C service_mvp generate 01_skafolding
