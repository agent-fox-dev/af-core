# Erratum: Workspace Dependency Syntax (Spec 10)

## Affected Requirements

- 10-REQ-1.4: speclib declares afspec as a path dependency pointing to
  `../afspec`
- 10-REQ-7.E1: spec-cli declares speclib as a path dependency pointing
  to `../speclib`

## Divergence

The spec and test specification (TS-10-14, TS-10-E9) prescribe using
path references in each package's `[tool.uv.sources]`:

```toml
# speclib/pyproject.toml (as specified)
[tool.uv.sources]
afspec = { path = "../afspec", editable = true }

# spec-cli/pyproject.toml (as specified)
[tool.uv.sources]
speclib = { path = "../speclib", editable = true }
```

The implementation uses workspace references instead:

```toml
# speclib/pyproject.toml (as implemented)
[tool.uv.sources]
afspec = { workspace = true }

# spec-cli/pyproject.toml (as implemented)
[tool.uv.sources]
speclib = { workspace = true }
```

## Rationale

Requirement 10-REQ-4.4 requires that `uv run pytest` works from within
each package directory. This requires the root `pyproject.toml` to
declare a `[tool.uv.workspace]` section with `members = ["packages/*"]`.

When a uv workspace is configured, member packages that depend on each
other **must** use `{ workspace = true }` syntax rather than direct
`{ path = "..." }` references. Using path references within a workspace
causes uv to error:

```
`speclib` is included as a workspace member, but references a path in
`tool.uv.sources`. Workspace members must be declared as workspace
sources (e.g., `speclib = { workspace = true }`).
```

The root `pyproject.toml` retains the path declarations that resolve
actual package locations:

```toml
[tool.uv.sources]
afspec = { path = "packages/afspec", editable = true }
speclib = { path = "packages/speclib", editable = true }
spec-cli = { path = "packages/spec-cli", editable = true }
```

## Impact

The intent of the requirements (local path dependency rather than
registry) is fully preserved. The dependency resolution behavior is
identical — only the syntax differs due to uv workspace constraints.
