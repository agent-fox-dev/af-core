---
spec_id: "11"
spec_name: "mvp_execution"
title: "MVP Spec Execution — Local CLI"
status: draft
created_at: "2026-06-12T20:00:00Z"
updated_at: "2026-06-12T20:00:00Z"
owner: "michael"
source: "Architecture decision to build a minimalistic MVP that can execute a spec pack locally"
supersedes: []
tags: ["mvp", "execution", "cli"]
intent_hash: null
schema_version: 1
---

## Background

The af-core project has a working spec authoring pipeline: the `spec` CLI
drives speclib to create campaigns, assess PRDs, generate requirements /
test_spec / tasks artifacts, and validate spec packages. What does not
exist yet is the execution side — taking an approved spec pack and running
an agent to implement it.

The full architecture (docs/runtime-layer.md, docs/coordination-layer.md,
docs/services-architecture.md) envisions a hub, sandboxes, the af SDK, a
two-tier harness adapter model, campaigns with dependency graphs, and
multi-agent orchestration. None of that is needed for an MVP. The goal is
the simplest possible execution path that is still spec-driven and correct.

The existing packages are:

- `afspec` — spec format models, validation, rendering, lifecycle, discovery
- `speclib` — agent pipeline (assessment, generation), sessions, campaigns
- `spec-cli` — the `spec` command (authoring-only today)

The example spec pack at `examples/golang_service/service_mvp/` is the
reference target: a campaign with one spec (`01_skafolding`) that defines a
minimal Go service. The MVP must be able to take this spec pack and produce
a working implementation.

## Intent

Extend the `spec` CLI with a `run` subcommand that executes an approved
spec pack locally, using a single AI agent to implement each subtask in
order. No hub, no sandbox, no gRPC, no af SDK — the agent reads the spec
directly from the filesystem and writes code into a local git branch. This
is the simplest execution path that still follows the spec-driven model:
frozen plan, ordered task groups, verification checks.

## Goals

1. Add a `spec run` command that takes an approved spec within a campaign
   and executes it against a local repository checkout.
2. Create a workspace branch, clone/checkout the repo, and run a single
   agent that implements subtasks in task-group order.
3. Track subtask execution state in a local state file alongside the spec
   artifacts (not in a database).
4. After each task group, run the group's verification checks. On failure,
   surface the error and stop (no automatic re-delegation in the MVP).
5. Support the Claude Agent SDK as the initial adapter (Tier 1). The
   generic LangGraph adapter is out of scope for the MVP.
6. Inject the relevant spec slice into the agent's system prompt before
   each subtask — the frozen requirements, test spec entries, and task
   details the subtask traces to.
7. On completion (all task groups done, wiring verification passed), commit
   the work and report ready for review.

## Non-Goals

- No hub process. Everything runs in-process within the CLI.
- No OpenShell sandboxes. The agent runs directly on the local filesystem.
- No af SDK / gRPC. The agent reads spec artifacts directly from disk.
- No Contexts or grounding. The agent has no attached Context sources.
- No agent memory. No recall or consolidate.
- No campaign dependency graphs. Only single-spec execution.
- No multi-agent orchestration. One agent, sequential subtask execution.
- No resume/suspend. If interrupted, re-run from the beginning (or from
  the last committed task group, using git state).
- No web dashboard, notification service, or retrieval engine.
- No Google ADK or generic LangGraph adapter — Claude Agent SDK only.
- No operational store (SQLite). State is a JSON file on disk.
- No prompt assembly from the coordination layer. The CLI composes the
  system prompt directly from the spec artifacts.

## User Flow

```
# 1. Author the spec (already working)
spec init my-campaign
spec new my-campaign --prd prd.md
spec assess my-campaign 01
spec generate my-campaign 01
spec validate my-campaign 01
spec approve my-campaign 01

# 2. Execute the spec (this PRD)
spec run my-campaign 01 --repo /path/to/target/repo

# What happens:
#   - CLI reads the approved spec pack from the campaign directory
#   - CLI creates branch af/01_skafolding from the repo's default branch
#   - CLI checks out the branch
#   - For each task group (in order):
#     - For each subtask in the group:
#       - CLI composes a system prompt with the subtask details,
#         traced requirements, and traced test spec entries
#       - CLI runs the Claude Agent SDK to implement the subtask
#       - CLI marks the subtask as done in the state file
#     - CLI runs the group's verification checks
#     - On failure: report error, stop
#     - On success: commit the work, continue to next group
#   - After all groups: report ready for review
```

## Execution Model

### Spec reading

The CLI reads the four spec artifacts directly from the campaign's spec
directory on disk. No hub, no gRPC, no af SDK. The spec must be in
`active` status (approved). The CLI uses afspec's existing models and
validation to load and validate the spec.

### Branch management

The CLI creates a git branch named `af/<spec_slug>` (e.g. `af/01_skafolding`)
from the repo's default branch. It checks out this branch in the target
repository directory. The user's current checkout is modified — there is no
sandbox isolation in the MVP.

### Agent execution

The CLI uses the Claude Agent SDK to run a single agent per subtask. For
each subtask:

1. Compose a system prompt containing:
   - The specialist role (Implementor) and basic instructions
   - The full subtask details (from tasks.json)
   - The requirements this subtask traces to (from requirements.json)
   - The test spec entries this subtask traces to (from test_spec.json)
   - The test commands (from tasks.json `test_commands`)
2. Run the Claude Agent SDK with this prompt and standard coding tools
   (file read/write, shell execution, git).
3. Wait for the agent to complete.
4. Mark the subtask as done in the state file.

The agent has full access to the local filesystem (no sandbox). It can
read and write files, run shell commands, and use git. It does NOT have
access to external MCP servers, Contexts, or the af SDK tools.

### Verification

After all subtasks in a task group complete, the CLI runs the group's
verification checks (from the `verification.checks` array in tasks.json).
Each check is a human-readable assertion. In the MVP, verification runs
the test commands defined in `tasks.json.test_commands`:

- `spec_tests` after each test group
- `all_tests` after the wiring verification group
- `linter` after the wiring verification group

On failure, the CLI reports the failing check and stops. The user can fix
manually and re-run.

### State tracking

Subtask execution state is tracked in a `_run.json` file in the spec
directory (alongside `_session.json`). This file records:

- Which subtasks have been completed
- Which task group is currently active
- Timestamps for each transition
- The branch name

This allows a re-run to skip already-completed task groups (by checking
git state and the run file).

### Commit discipline

The CLI commits after each completed task group (not after each subtask).
The commit message follows the convention:
`feat(<spec_slug>): complete task group <N> — <title>`

## Technical Constraints

- Python 3.14+, consistent with the existing codebase
- Claude Agent SDK (`anthropic` Python package) — already a dependency
  of speclib for the authoring pipeline
- No new infrastructure dependencies (no database, no gRPC, no containers)
- The execution logic lives in speclib (as a new module), not in spec-cli
  (the CLI is a thin wrapper)
- The agent's tool set is whatever the Claude Agent SDK provides by default
  (file editing, shell, git) — no custom tools in the MVP

## Success Criteria

The MVP is successful when:

1. `spec run` can take the `examples/golang_service/service_mvp/` spec
   pack and produce a working Go service that passes all verification
   checks defined in the spec.
2. The execution follows the task group order defined in tasks.json.
3. Each subtask's agent receives only the spec slice relevant to that
   subtask (not the entire spec).
4. Verification checks run after each task group and fail loudly on error.
5. The result is committed on a dedicated branch with clean commit history.
