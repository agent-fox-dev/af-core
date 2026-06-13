# Requirements Document

## Introduction

This document specifies the spec analysis and execution planning layer for
the coder tool. It covers reading spec packs from a campaign directory,
analyzing inter-spec dependencies, determining implementation order, and
producing a structured execution plan.

## Glossary

- **Campaign Directory**: A filesystem directory containing one or more spec
  pack folders, each following the `NN_snake_case_name` naming convention.
- **Spec Pack**: A folder containing spec artifacts: `prd.md`,
  `requirements.json`, `test_spec.json`, `tasks.json`.
- **Execution Plan**: An ordered list of spec packs with their parsed
  artifacts, ready for sequential implementation by the TDD engine.
- **Dependency Graph**: A directed acyclic graph representing dependencies
  between spec packs, derived from `tasks.json` dependency declarations.
- **Topological Sort**: An ordering of specs such that every dependency is
  implemented before its dependent.
- **Spec Status**: The lifecycle state of a spec (`draft`, `active`,
  `sealed`, `superseded`, `archived`). Only `active` specs are executable.
- **SpecMeta**: Metadata about a discovered spec (ID, name, status, path).

## Requirements

### Requirement 1: Campaign Directory Discovery

**User Story:** As a user, I want the coder to automatically find all spec
packs in a campaign directory, so that I don't have to specify each spec
individually.

#### Acceptance Criteria

[13-REQ-1.1] WHEN a campaign directory path is provided, THE system SHALL
discover all spec pack folders matching the `NN_snake_case_name` pattern
AND return a list of `SpecMeta` objects with spec ID, name, status, and
directory path.

[13-REQ-1.2] THE system SHALL use `afspec.discovery.discover_specs()` for
spec folder discovery to reuse existing validated logic.

[13-REQ-1.3] THE system SHALL sort discovered specs by their numeric prefix
in ascending order.

#### Edge Cases

[13-REQ-1.E1] IF the campaign directory is empty (no spec pack folders),
THEN THE system SHALL return an empty list without error.

[13-REQ-1.E2] IF the campaign directory contains non-spec folders (not
matching the `NN_name` pattern), THEN THE system SHALL ignore them.

---

### Requirement 2: Spec Pack Parsing

**User Story:** As a developer, I want spec packs parsed into structured
models, so that downstream components can access requirements, tests, and
tasks programmatically.

#### Acceptance Criteria

[13-REQ-2.1] WHEN a spec pack folder is parsed, THE system SHALL load
`requirements.json` into an `afspec.models.Requirements` model AND return
the parsed model to the caller.

[13-REQ-2.2] WHEN a spec pack folder is parsed, THE system SHALL load
`test_spec.json` into an `afspec.models.TestSpec` model AND return the
parsed model to the caller.

[13-REQ-2.3] WHEN a spec pack folder is parsed, THE system SHALL load
`tasks.json` into an `afspec.models.Tasks` model AND return the parsed
model to the caller.

[13-REQ-2.4] WHEN a spec pack folder is parsed, THE system SHALL load
`prd.md` as raw text AND return it to the caller.

[13-REQ-2.5] THE system SHALL return a `ParsedSpec` record containing
all parsed artifacts (requirements, test_spec, tasks, prd_text) along
with the spec's metadata AND make it available to the execution plan.

#### Edge Cases

[13-REQ-2.E1] IF a required JSON file (`requirements.json`, `test_spec.json`,
or `tasks.json`) is missing from a spec pack folder, THEN THE system SHALL
raise a `SpecParseError` identifying the missing file and spec name.

[13-REQ-2.E2] IF a JSON file contains invalid JSON syntax, THEN THE system
SHALL raise a `SpecParseError` with the file path and parse error details.

[13-REQ-2.E3] IF `prd.md` is missing, THEN THE system SHALL set
`prd_text` to an empty string and log a warning.

---

### Requirement 3: Spec Status Validation

**User Story:** As a user, I want the coder to only execute specs that are
ready for implementation, so that draft or archived specs are not
accidentally processed.

#### Acceptance Criteria

[13-REQ-3.1] WHEN building an execution plan, THE system SHALL include only
specs with status `active` AND skip all other statuses.

[13-REQ-3.2] WHEN a spec is skipped due to non-active status, THE system
SHALL log a warning including the spec name and its current status.

[13-REQ-3.3] IF all specs in the campaign have non-active status, THEN THE
system SHALL return an empty execution plan and log an error message.

#### Edge Cases

[13-REQ-3.E1] IF a spec's status cannot be determined (missing or invalid
status field), THEN THE system SHALL treat it as `draft` and skip it with
a warning.

---

### Requirement 4: Dependency Analysis

**User Story:** As a user, I want specs implemented in the correct order
based on their dependencies, so that each spec can build on the output of
its predecessors.

#### Acceptance Criteria

[13-REQ-4.1] THE system SHALL build a dependency graph from `tasks.json`
dependency declarations across all active specs in the campaign, using
`afspec.discovery.build_dependency_graph()`.

[13-REQ-4.2] THE system SHALL compute a topological sort of the dependency
graph AND return specs in an order where every dependency precedes its
dependent.

[13-REQ-4.3] IF the dependency graph contains a cycle, THEN THE system
SHALL raise a `DependencyCycleError` listing the specs involved in the
cycle.

[13-REQ-4.4] WHEN multiple valid topological orderings exist, THE system
SHALL prefer the ordering that preserves the numeric prefix order (lowest
spec number first among peers with no dependency relationship).

#### Edge Cases

[13-REQ-4.E1] IF a spec declares a dependency on a spec not present in the
campaign, THEN THE system SHALL log a warning and treat the dependency as
satisfied (assume the external spec was already implemented).

[13-REQ-4.E2] IF no specs have dependencies, THEN THE system SHALL order
them by numeric prefix (ascending).

---

### Requirement 5: Execution Plan Model

**User Story:** As a developer, I want the planning output to be a
well-structured data model, so that the TDD engine can consume it
directly.

#### Acceptance Criteria

[13-REQ-5.1] THE system SHALL produce an `ExecutionPlan` record containing:
an ordered list of `ParsedSpec` objects, the total spec count, and a
timestamp AND return it to the caller.

[13-REQ-5.2] EACH `ParsedSpec` in the execution plan SHALL contain: the
spec metadata (`SpecMeta`), parsed requirements, parsed test_spec, parsed
tasks, and prd text.

[13-REQ-5.3] THE `ExecutionPlan` SHALL be a frozen pydantic model that is
serializable to JSON for debugging and logging purposes.

#### Edge Cases

[13-REQ-5.E1] IF the execution plan is empty (no active specs), THEN THE
`ExecutionPlan` SHALL have an empty specs list and a count of zero.

---

### Requirement 6: Plan Builder Entry Point

**User Story:** As a developer, I want a single function that takes a
campaign directory and returns an execution plan, so that the CLI and
engine can call it directly.

#### Acceptance Criteria

[13-REQ-6.1] THE system SHALL provide a `build_execution_plan(campaign_dir)`
function that discovers specs, parses them, validates status, analyzes
dependencies, and returns an `ExecutionPlan` AND logs each step of the
process.

[13-REQ-6.2] THE `build_execution_plan` function SHALL accept an optional
`spec_filter` parameter (list of spec names) to restrict which specs are
included in the plan.

#### Edge Cases

[13-REQ-6.E1] IF the campaign directory does not exist, THEN THE function
SHALL raise a `FileNotFoundError`.
