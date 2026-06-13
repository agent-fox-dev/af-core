# Requirements Document

## Introduction

This document specifies the core TDD execution engine for the coder tool —
a LangGraph state machine that takes a parsed spec pack and produces a
working implementation through test-driven development. It covers the graph
workflow, coding tools, worktree management, verification, and git
operations.

## Glossary

- **LangGraph**: A library for building stateful, multi-step agent
  applications as directed graphs with nodes (steps) and edges (transitions).
- **Graph State**: A typed dictionary maintained across all nodes in the
  LangGraph execution, containing the current step, task group, attempt
  counts, test results, and code context.
- **Node**: A function in the LangGraph graph that performs one step of the
  workflow (e.g., `write_tests`, `implement`, `verify_intent`).
- **Conditional Edge**: A graph edge that routes to different nodes based
  on the current state (e.g., test failure routes back to `implement`).
- **TDD Cycle**: The test-driven development loop: write failing tests →
  implement code → verify tests pass → verify intent.
- **Worktree**: A git worktree — an additional checkout of the repository
  at a different path, allowing isolated work without affecting the main
  working directory.
- **Verification Runner**: A component that executes shell commands from
  the spec pack's `test_commands` and reports pass/fail status.
- **Task Group**: A logical unit of work within a spec, containing related
  subtasks that are implemented together.
- **Run State**: A JSON file (`_run.json`) tracking execution progress for
  debugging and potential resumability.

## Requirements

### Requirement 1: LangGraph State Schema

**User Story:** As a developer, I want the workflow state to be explicitly
typed, so that each node can access and update shared execution context.

#### Acceptance Criteria

[14-REQ-1.1] THE system SHALL define a `CoderState` TypedDict for LangGraph
containing: `current_phase` (str), `current_task_group` (int),
`attempt_count` (int), `max_attempts` (int), `test_results` (str),
`spec_context` (str), `codebase_analysis` (str), `messages` (list),
`halted` (bool), `halt_reason` (str).

[14-REQ-1.2] THE `CoderState` SHALL be initialized with `attempt_count=0`,
`halted=False`, and `current_phase="understand_spec"` before graph
execution begins.

#### Edge Cases

[14-REQ-1.E1] IF any state field is missing when a node reads it, THEN THE
node SHALL use a sensible default (empty string for str, 0 for int, False
for bool) rather than raising a KeyError.

---

### Requirement 2: LangGraph Workflow Nodes

**User Story:** As a user, I want the coding workflow to follow the 9-step
TDD process defined in the PRD, so that the agent produces well-tested code.

#### Acceptance Criteria

[14-REQ-2.1] THE graph SHALL contain a `understand_spec` node that reads the
spec pack (PRD, requirements, test_spec) and produces a summary of the
spec's intent, writing it to `spec_context` in the state AND returning the
updated state.

[14-REQ-2.2] THE graph SHALL contain an `analyze_codebase` node that examines
the current codebase in the worktree and produces an analysis of existing
code structure, writing it to `codebase_analysis` in the state AND returning
the updated state.

[14-REQ-2.3] THE graph SHALL contain a `write_tests` node that instructs the
LLM to create failing tests based on the spec's `test_spec` entries for the
current task group AND returning the updated state.

[14-REQ-2.4] THE graph SHALL contain a `verify_test_coverage` node that
instructs the LLM to check whether the written tests cover all test cases
defined in the spec for the current task group AND set a `coverage_ok`
flag in the state.

[14-REQ-2.5] THE graph SHALL contain an `implement` node that instructs the
LLM to write implementation code to make the current task group's tests
pass AND returning the updated state.

[14-REQ-2.6] THE graph SHALL contain a `run_tests` node that executes the
verification runner (spec_tests command) and writes pass/fail results to
the state AND returning the updated state.

[14-REQ-2.7] THE graph SHALL contain a `verify_intent` node that uses the
`reviewer` persona to check whether the implementation fulfills the spec's
intent AND set a `drift_detected` flag in the state.

#### Edge Cases

[14-REQ-2.E1] IF the LLM returns an empty or unparseable response in any
node, THEN THE node SHALL increment `attempt_count` and route to retry
rather than crashing.

---

### Requirement 3: Conditional Edge Routing

**User Story:** As a developer, I want the workflow to automatically retry
or loop back when tests fail or drift is detected, so that the agent
iterates toward a correct solution.

#### Acceptance Criteria

[14-REQ-3.1] WHEN `verify_test_coverage` determines coverage is
insufficient, THE graph SHALL route back to `write_tests`.

[14-REQ-3.2] WHEN `run_tests` reports test failures, THE graph SHALL route
back to `implement` with incremented `attempt_count`.

[14-REQ-3.3] WHEN `run_tests` reports all tests passing, THE graph SHALL
route to `verify_intent`.

[14-REQ-3.4] WHEN `verify_intent` detects spec drift, THE graph SHALL
route back to `verify_test_coverage` with incremented `attempt_count`.

[14-REQ-3.5] WHEN `verify_intent` confirms no drift, THE graph SHALL
route to `next_task_group` or `complete` if all groups are done.

[14-REQ-3.6] WHEN `attempt_count` exceeds `max_attempts`, THE graph SHALL
set `halted=True` with a reason and route to a terminal `halted` node
instead of retrying.

#### Edge Cases

[14-REQ-3.E1] IF `halted` is True at any node entry, THEN THE node SHALL
immediately return the state unchanged and allow routing to the terminal
node.

---

### Requirement 4: LangChain Coding Tools

**User Story:** As an agent, I need file I/O and shell access tools, so
that I can read and modify code and run tests.

#### Acceptance Criteria

[14-REQ-4.1] THE system SHALL provide a `read_file` tool that reads a file
at a given path relative to the worktree root AND returns the file contents
as a string.

[14-REQ-4.2] THE system SHALL provide a `write_file` tool that writes
content to a file at a given path relative to the worktree root AND creates
parent directories if they don't exist.

[14-REQ-4.3] THE system SHALL provide a `run_command` tool that executes a
shell command in the worktree directory AND returns stdout, stderr, and exit
code.

[14-REQ-4.4] THE system SHALL provide a `list_directory` tool that lists
files and directories at a given path AND returns the listing as a
formatted string.

[14-REQ-4.5] WHEN a tool receives a path argument, THE system SHALL resolve
it relative to the worktree root AND reject paths that traverse above the
worktree root (no `..` escaping).

#### Edge Cases

[14-REQ-4.E1] IF `run_command` exceeds a 120-second timeout, THEN THE tool
SHALL kill the process and return a timeout error message.

[14-REQ-4.E2] IF `read_file` is called with a path to a binary file, THEN
THE tool SHALL return an error message indicating the file is binary.

[14-REQ-4.E3] IF `write_file` is called with a path that is a symlink, THEN
THE tool SHALL reject the write and return a security error.

---

### Requirement 5: Worktree Lifecycle

**User Story:** As a user, I want the agent to work in an isolated git
worktree, so that my main working directory is not affected during execution.

#### Acceptance Criteria

[14-REQ-5.1] WHEN execution begins, THE system SHALL create a git worktree
from the current branch at `.coder/worktrees/<spec_slug>` with a branch
named `coder/<model_name>/<spec_slug>`.

[14-REQ-5.2] THE system SHALL perform all file operations and test execution
within the worktree directory, not the original repository.

[14-REQ-5.3] WHEN execution completes successfully (all tests pass, no
drift), THE system SHALL merge the worktree branch back into the source
branch using fast-forward merge AND return a success indicator.

[14-REQ-5.4] WHEN the worktree is successfully merged, THE system SHALL
remove the worktree directory and prune the worktree registry.

[14-REQ-5.5] IF fast-forward merge fails (branches have diverged), THEN
THE system SHALL leave the worktree in place, log an error with merge
details, and report the failure.

#### Edge Cases

[14-REQ-5.E1] IF the worktree directory already exists (stale from a
previous run), THEN THE system SHALL remove it before creating a new one.

[14-REQ-5.E2] IF worktree creation fails (git error), THEN THE system
SHALL raise a `WorktreeError` with the git error output.

---

### Requirement 6: Verification Runner

**User Story:** As a user, I want tests automatically executed after each
implementation step, so that I can see progress toward a passing suite.

#### Acceptance Criteria

[14-REQ-6.1] THE verification runner SHALL execute shell commands from the
spec's `tasks.test_commands` section in this order: `spec_tests` (after
each task group), `all_tests` and `linter` (after the final group).

[14-REQ-6.2] THE runner SHALL capture stdout, stderr, and exit code from
each command AND return a `VerificationResult` containing these values and
a pass/fail boolean.

[14-REQ-6.3] THE runner SHALL consider exit code 0 as pass and any non-zero
exit code as fail.

[14-REQ-6.4] THE runner SHALL enforce a configurable timeout per command
(default 300 seconds) AND return a timeout failure if exceeded.

#### Edge Cases

[14-REQ-6.E1] IF a test command string is empty or null in `tasks.json`,
THEN THE runner SHALL skip that command and log a warning.

[14-REQ-6.E2] IF the test command binary is not found (e.g., `go` not
installed), THEN THE runner SHALL return a fail result with the error
message rather than crashing.

---

### Requirement 7: Task Group Iteration

**User Story:** As a user, I want the agent to process each task group in
order, making incremental progress through the spec.

#### Acceptance Criteria

[14-REQ-7.1] THE system SHALL iterate through task groups in the order
defined in `tasks.json`, processing group 1 (tests) first, then subsequent
groups.

[14-REQ-7.2] WHEN a task group completes (all tests pass), THE system SHALL
commit all changes with message format:
`feat(<spec_slug>): complete task group <N> — <title>`.

[14-REQ-7.3] WHEN a task group completes, THE system SHALL advance
`current_task_group` in the state and reset `attempt_count` to 0.

[14-REQ-7.4] WHEN all task groups are complete and verified, THE system
SHALL set `current_phase` to `"complete"` in the state.

#### Edge Cases

[14-REQ-7.E1] IF a commit fails (e.g., nothing to commit), THEN THE system
SHALL log a warning and continue to the next group.

---

### Requirement 8: Run State Persistence

**User Story:** As a user, I want execution state saved to disk, so that
I can inspect progress and debug failures.

#### Acceptance Criteria

[14-REQ-8.1] THE system SHALL persist run state to `_run.json` in the
worktree root after every node transition, containing: current phase,
task group, attempt count, timestamps, test results, and halt status.

[14-REQ-8.2] THE `_run.json` SHALL include a `history` array of all
previous state transitions with timestamps for debugging.

[14-REQ-8.3] THE system SHALL write `_run.json` atomically (write to
temp file, then rename) to prevent corruption on crash.

#### Edge Cases

[14-REQ-8.E1] IF writing `_run.json` fails (e.g., disk full), THEN THE
system SHALL log a warning and continue execution rather than crashing.

---

### Requirement 9: Graph Construction Entry Point

**User Story:** As a developer, I want a single function to build and run
the LangGraph workflow for a given spec, so that the outer loop can call
it for each spec in the plan.

#### Acceptance Criteria

[14-REQ-9.1] THE system SHALL provide a `run_spec(parsed_spec, provider,
worktree_path, config)` function that constructs the LangGraph, initializes
state, and executes the workflow AND returns a `RunResult` with success/fail
status, final state, and run statistics.

[14-REQ-9.2] THE `RunResult` SHALL contain: `success` (bool),
`task_groups_completed` (int), `total_task_groups` (int), `total_tokens`
(int), `elapsed_seconds` (float), `halt_reason` (str or null).

[14-REQ-9.3] THE system SHALL provide a `run_campaign(execution_plan,
provider, repo_path, config)` function that iterates over specs in plan
order, calling `run_spec` for each, managing worktrees, and collecting
results AND returning a list of `RunResult` objects.

#### Edge Cases

[14-REQ-9.E1] IF `run_spec` fails with an unhandled exception, THEN
`run_campaign` SHALL catch the exception, record it as a failed run
result, and continue to the next spec.
