# PRD: Spec Analysis & Execution Planning

## Intent

Enable the coder tool to read a campaign directory containing spec packs,
analyze dependencies between specs, determine the correct implementation
order, and produce a structured execution plan that the TDD engine (spec 14)
will consume.

## Goals

1. Read and parse spec packs from a campaign directory using `afspec` models
   and discovery utilities.
2. Analyze inter-spec dependencies from `tasks.json` dependency declarations.
3. Determine implementation order via topological sort of the dependency graph.
4. Validate that all specs in the campaign are in a valid state for execution
   (status must be `active`).
5. Produce a structured execution plan (ordered list of specs with parsed
   artifacts) that downstream components consume.

## Non-Goals

- No LLM calls in this spec — planning is deterministic, based on spec metadata.
- No execution of specs (deferred to spec 14).
- No prompt assembly or provider calls.
- No parallel execution planning — sequential order only for MVP.
- No modification of spec files — read-only access.

## Background

The af-core project's `afspec` package provides models for spec artifacts
(`Requirements`, `TestSpec`, `Tasks`, `TaskGroup`, `Subtask`) and discovery
utilities (`discover_specs`, `build_dependency_graph`). The coder tool should
reuse these rather than reimplementing spec parsing.

A campaign directory contains one or more spec pack folders, each with
`prd.md`, `requirements.json`, `test_spec.json`, and `tasks.json`. The
`tasks.json` file includes dependency declarations that define which spec
groups must complete before others can start.

For the MVP, specs are executed sequentially in dependency order. If spec A
depends on spec B, spec B is implemented first. Circular dependencies are
an error.

## Design Decisions

1. **Reuse afspec.discovery**: The `discover_specs()` function already finds
   spec folders matching `NN_snake_case_name`. The `build_dependency_graph()`
   function constructs a directed dependency graph. Both are reused as-is.
2. **Reuse afspec.models**: Spec artifacts are parsed into `afspec` pydantic
   models (`Requirements`, `TestSpec`, `Tasks`). No custom parsing needed.
3. **JSON format only**: Spec packs use JSON for structured data
   (`requirements.json`, `test_spec.json`, `tasks.json`). The PRD is markdown
   (`prd.md`). The coder reads both.
4. **Active status required**: Only specs with `active` status are eligible
   for execution. Draft, sealed, or archived specs are skipped with a warning.
5. **Execution plan as data class**: The plan is a pydantic model containing
   the ordered list of specs with their parsed artifacts, ready for the
   execution engine to consume.

## Dependencies

| Spec | From Group | To Group | Relationship |
|------|-----------|----------|--------------|
| 12_coder_foundation | 2 | 1 | Uses provider config and logging infrastructure from group 2 |

## Source

Source: Input provided by user via interactive prompt.
