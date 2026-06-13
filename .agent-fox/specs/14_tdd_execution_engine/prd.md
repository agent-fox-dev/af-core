# PRD: TDD Execution Engine (LangGraph)

## Intent

Implement the core coding workflow as a LangGraph state machine that takes a
spec pack and produces a working implementation using test-driven development.
The workflow encodes the full 9-step TDD cycle as graph nodes with conditional
edges for retry and loop-back, and manages git worktrees for isolated execution.

## Goals

1. Encode the full TDD coding workflow as a LangGraph state machine:
   understand spec → analyze codebase → write tests → verify test coverage →
   implement → run tests → verify intent, with conditional retry edges.
2. Implement LangChain tools for coding: file read/write, shell execution,
   and git operations — uniform across all LLM providers.
3. Manage git worktree lifecycle: create worktree from current branch before
   execution, work within it, commit after each task group, merge back on
   completion, clean up on success.
4. Implement a verification runner that executes test commands from the spec
   pack's `tasks.json` and parses results to determine success/failure.
5. Support task group iteration: process spec tasks in group order, with each
   group going through the TDD cycle.
6. Persist run state to a JSON file for resumability and debugging.

## Non-Goals

- No circuit breakers or post-mortem generation (deferred to spec 15).
- No token tracking or budget enforcement (deferred to spec 15).
- No parallel execution of task groups — strictly sequential.
- No multi-spec orchestration in this spec — handles one spec at a time.
  The outer loop (iterating over the execution plan from spec 13) is in the
  CLI integration, not in the LangGraph workflow.
- No agent memory or knowledge system.

## Background

The user's specified workflow has 9 steps:

1. Understand the spec and its intention.
2. Analyze the current codebase to plan implementation.
3. Create all tests the spec defines first (tests expected to FAIL).
4. Verify tests cover the defined test cases; loop back to 3 if not.
5. Implementation starts once tests are in place and valid.
6. Agent creates code, working through tasks defined in the spec pack.
7. Each task group has tests; passing tests = success criteria. If tests fail,
   loop back to 6.
8. Once all task groups are implemented, ALL tests from step 3 must pass. If
   not, loop back to 6.
9. Verify code fulfills spec intent. If drift detected, loop back to 4.

This maps naturally to a LangGraph state machine where each step is a node,
and conditional edges encode the retry/loop-back logic.

Agent-fox uses a worktree-per-task-group model. For the coder MVP, we use one
worktree per spec execution run. The worktree is created from the current
branch, all work happens inside it, and on success it is merged back.

## Design Decisions

1. **Full LangGraph state machine**: The 9-step workflow is encoded as graph
   nodes with conditional edges. State includes: current step, current task
   group, attempt counts, test results, and code analysis context. This makes
   the workflow inspectable and debuggable through LangGraph's built-in
   tracing.
2. **One worktree per run**: A single worktree is created for the entire spec
   execution. All task groups are implemented sequentially in the same
   worktree. On success, the worktree branch is merged into the source branch.
3. **LangChain tools**: The coding agent uses LangChain's `@tool` decorator to
   define file read/write, shell execution, and git operations. These tools
   work identically regardless of the underlying LLM provider.
4. **Two agent personas**: The workflow uses two personas from the prompt
   template system (spec 12):
   - `coder` — for steps 1-8 (understanding, coding, testing).
   - `reviewer` — for step 9 (intent verification). A separate persona
     provides an independent perspective on spec compliance.
5. **Verification runner**: Executes shell commands from `tasks.json`'s
   `test_commands` section (`spec_tests`, `all_tests`, `linter`). Captures
   stdout/stderr and exit code. Success = exit code 0.
6. **Merge strategy**: Fast-forward merge preferred. If fast-forward fails
   (diverged branches), the merge attempt fails and is reported as an error.
   Conflict resolution is out of scope for MVP.
7. **Run state file**: `_run.json` persisted in the worktree root after each
   step transition. Contains: current node, task group, attempt counts, test
   results, timestamps. Enables post-mortem analysis (spec 15) and future
   resumability.
8. **Commit discipline**: One commit per completed task group. Message format:
   `feat(<spec_slug>): complete task group <N> — <title>`.

## Dependencies

| Spec | From Group | To Group | Relationship |
|------|-----------|----------|--------------|
| 12_coder_foundation | 3 | 1 | Uses provider registry, prompt assembly, and logging from group 3; group 3 is where the provider registry and prompt assembly are implemented |
| 13_spec_analysis_planning | 2 | 1 | Consumes ExecutionPlan data model from group 2; group 2 is where the execution plan model is defined |

## Source

Source: Input provided by user via interactive prompt.
