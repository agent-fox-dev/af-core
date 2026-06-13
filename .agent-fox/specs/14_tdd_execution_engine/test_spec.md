# Test Specification: TDD Execution Engine (LangGraph)

## Overview

Tests cover the LangGraph state machine, individual node behavior,
conditional edge routing, LangChain tools, worktree lifecycle, verification
runner, task group iteration, and run state persistence. Mock LLM providers
are used to avoid real API calls. Temporary git repos are used for worktree
tests.

## Test Cases

### TS-14-1: CoderState initializes with defaults

**Requirement:** 14-REQ-1.1, 14-REQ-1.2
**Type:** unit
**Description:** Verify CoderState has correct initial values.

**Preconditions:**
- None.

**Input:**
- Create initial `CoderState`.

**Expected:**
- `current_phase` = `"understand_spec"`, `attempt_count` = 0,
  `halted` = False.

**Assertion pseudocode:**
```
state = create_initial_state(parsed_spec)
ASSERT state["current_phase"] == "understand_spec"
ASSERT state["attempt_count"] == 0
ASSERT state["halted"] == False
```

---

### TS-14-2: understand_spec node populates spec_context

**Requirement:** 14-REQ-2.1
**Type:** unit
**Description:** Verify the understand_spec node writes to spec_context.

**Preconditions:**
- Mock LLM returns "Spec intent summary".

**Input:**
- Call `understand_spec(state)`.

**Expected:**
- State `spec_context` is non-empty.
- State `current_phase` updated.

**Assertion pseudocode:**
```
mock_llm.return_value = "Spec intent summary"
new_state = understand_spec(state, mock_llm)
ASSERT len(new_state["spec_context"]) > 0
```

---

### TS-14-3: analyze_codebase node populates analysis

**Requirement:** 14-REQ-2.2
**Type:** unit
**Description:** Verify the analyze node writes codebase analysis.

**Preconditions:**
- Mock LLM returns "Codebase analysis".

**Input:**
- Call `analyze_codebase(state)`.

**Expected:**
- State `codebase_analysis` is non-empty.

**Assertion pseudocode:**
```
mock_llm.return_value = "Codebase analysis"
new_state = analyze_codebase(state, mock_llm)
ASSERT len(new_state["codebase_analysis"]) > 0
```

---

### TS-14-4: write_tests node invokes LLM with test spec

**Requirement:** 14-REQ-2.3
**Type:** unit
**Description:** Verify write_tests sends test_spec content to LLM.

**Preconditions:**
- Mock LLM configured. State has spec_context.

**Input:**
- Call `write_tests(state)`.

**Expected:**
- LLM was invoked with messages containing test spec content.

**Assertion pseudocode:**
```
new_state = write_tests(state, mock_llm)
ASSERT mock_llm.invoke.called
messages = mock_llm.invoke.call_args[0][0]
ASSERT any("test" in str(m) for m in messages)
```

---

### TS-14-5: verify_test_coverage sets coverage_ok flag

**Requirement:** 14-REQ-2.4
**Type:** unit
**Description:** Verify coverage check sets the flag.

**Preconditions:**
- Mock LLM returns coverage assessment.

**Input:**
- Call `verify_test_coverage(state)`.

**Expected:**
- State contains `coverage_ok` as boolean.

**Assertion pseudocode:**
```
mock_llm.return_value = "Coverage: all test cases covered"
new_state = verify_test_coverage(state, mock_llm)
ASSERT "coverage_ok" in new_state
ASSERT isinstance(new_state["coverage_ok"], bool)
```

---

### TS-14-6: implement node invokes LLM with coder persona

**Requirement:** 14-REQ-2.5
**Type:** unit
**Description:** Verify implement node uses coder persona.

**Preconditions:**
- Mock LLM and prompt assembler.

**Input:**
- Call `implement(state)`.

**Expected:**
- LLM was invoked with system prompt containing coder persona content.

**Assertion pseudocode:**
```
new_state = implement(state, mock_llm)
ASSERT mock_llm.invoke.called
```

---

### TS-14-7: run_tests node executes verification runner

**Requirement:** 14-REQ-2.6
**Type:** unit
**Description:** Verify run_tests calls the verification runner.

**Preconditions:**
- Mock verification runner returning pass result.

**Input:**
- Call `run_tests(state)`.

**Expected:**
- State `test_results` contains verification output.

**Assertion pseudocode:**
```
mock_runner.run.return_value = VerificationResult(passed=True, ...)
new_state = run_tests(state, mock_runner)
ASSERT "pass" in new_state["test_results"].lower()
```

---

### TS-14-8: verify_intent uses reviewer persona

**Requirement:** 14-REQ-2.7
**Type:** unit
**Description:** Verify intent check uses reviewer persona.

**Preconditions:**
- Mock LLM and prompt assembler.

**Input:**
- Call `verify_intent(state)`.

**Expected:**
- State `drift_detected` is a boolean.

**Assertion pseudocode:**
```
mock_llm.return_value = "No drift detected"
new_state = verify_intent(state, mock_llm)
ASSERT isinstance(new_state["drift_detected"], bool)
```

---

### TS-14-9: Coverage failure routes back to write_tests

**Requirement:** 14-REQ-3.1
**Type:** unit
**Description:** Verify routing on coverage failure.

**Preconditions:**
- State with `coverage_ok=False`.

**Input:**
- Call routing function after verify_test_coverage.

**Expected:**
- Next node is `write_tests`.

**Assertion pseudocode:**
```
state = {... "coverage_ok": False}
next_node = route_after_coverage(state)
ASSERT next_node == "write_tests"
```

---

### TS-14-10: Test failure routes back to implement

**Requirement:** 14-REQ-3.2
**Type:** unit
**Description:** Verify routing on test failure with attempts remaining.

**Preconditions:**
- State with test failure and `attempt_count < max_attempts`.

**Input:**
- Call routing function after run_tests.

**Expected:**
- Next node is `implement`.

**Assertion pseudocode:**
```
state = {... "test_results": "FAIL", "attempt_count": 1, "max_attempts": 5}
next_node = route_after_tests(state)
ASSERT next_node == "implement"
```

---

### TS-14-11: All tests pass routes to verify_intent

**Requirement:** 14-REQ-3.3
**Type:** unit
**Description:** Verify routing on test success.

**Preconditions:**
- State with all tests passing.

**Input:**
- Call routing function after run_tests.

**Expected:**
- Next node is `verify_intent`.

**Assertion pseudocode:**
```
state = {... "test_results": "PASS"}
next_node = route_after_tests(state)
ASSERT next_node == "verify_intent"
```

---

### TS-14-12: Max attempts triggers halt

**Requirement:** 14-REQ-3.6
**Type:** unit
**Description:** Verify max attempts routes to halted.

**Preconditions:**
- State with `attempt_count >= max_attempts`.

**Input:**
- Call routing function after run_tests.

**Expected:**
- Next node is `halted`.

**Assertion pseudocode:**
```
state = {... "attempt_count": 5, "max_attempts": 5, "test_results": "FAIL"}
next_node = route_after_tests(state)
ASSERT next_node == "halted"
```

---

### TS-14-13: read_file tool returns file contents

**Requirement:** 14-REQ-4.1
**Type:** unit
**Description:** Verify read_file tool reads from worktree.

**Preconditions:**
- Temporary directory with file `src/main.py` containing "hello".

**Input:**
- `read_file("src/main.py")`.

**Expected:**
- Returns `"hello"`.

**Assertion pseudocode:**
```
write_file(worktree / "src/main.py", "hello")
result = read_file_tool.invoke({"path": "src/main.py"})
ASSERT result == "hello"
```

---

### TS-14-14: write_file tool creates file and parents

**Requirement:** 14-REQ-4.2
**Type:** unit
**Description:** Verify write_file creates directories and file.

**Preconditions:**
- Empty worktree directory.

**Input:**
- `write_file("src/new/main.py", "content")`.

**Expected:**
- File exists at `worktree/src/new/main.py` with content "content".

**Assertion pseudocode:**
```
write_file_tool.invoke({"path": "src/new/main.py", "content": "content"})
ASSERT (worktree / "src/new/main.py").read_text() == "content"
```

---

### TS-14-15: run_command tool executes in worktree

**Requirement:** 14-REQ-4.3
**Type:** unit
**Description:** Verify run_command executes in the worktree directory.

**Preconditions:**
- Worktree directory exists.

**Input:**
- `run_command("pwd")`.

**Expected:**
- stdout contains worktree path.

**Assertion pseudocode:**
```
result = run_command_tool.invoke({"command": "pwd"})
ASSERT str(worktree) in result
```

---

### TS-14-16: Path traversal rejected by tools

**Requirement:** 14-REQ-4.5
**Type:** unit
**Description:** Verify path escaping is blocked.

**Preconditions:**
- Worktree directory exists.

**Input:**
- `read_file("../../etc/passwd")`.

**Expected:**
- Returns error message about path traversal.

**Assertion pseudocode:**
```
result = read_file_tool.invoke({"path": "../../etc/passwd"})
ASSERT "error" in result.lower() or "denied" in result.lower()
```

---

### TS-14-17: Worktree created with correct branch name

**Requirement:** 14-REQ-5.1
**Type:** integration
**Description:** Verify worktree creation with expected branch naming.

**Preconditions:**
- Temporary git repository with at least one commit.

**Input:**
- `create_worktree(repo, "base_app", "claude-opus-4-6")`.

**Expected:**
- Worktree exists at `.coder/worktrees/base_app`.
- Branch name is `coder/claude-opus-4-6/base_app`.

**Assertion pseudocode:**
```
wt = create_worktree(repo, "base_app", "claude-opus-4-6")
ASSERT wt.path.exists()
ASSERT wt.branch == "coder/claude-opus-4-6/base_app"
```

---

### TS-14-18: Worktree merged on success

**Requirement:** 14-REQ-5.3
**Type:** integration
**Description:** Verify successful merge back to source branch.

**Preconditions:**
- Worktree with committed changes, source branch unchanged.

**Input:**
- `merge_worktree(worktree_info)`.

**Expected:**
- Source branch now contains the worktree changes.

**Assertion pseudocode:**
```
-- make changes and commit in worktree
result = merge_worktree(wt_info)
ASSERT result == True
-- verify source branch has the changes
```

---

### TS-14-19: Verification runner returns pass for exit 0

**Requirement:** 14-REQ-6.2, 14-REQ-6.3
**Type:** unit
**Description:** Verify exit code 0 maps to passed=True.

**Preconditions:**
- Worktree with a passing test command (`echo ok`).

**Input:**
- `VerificationRunner.run(TestCommands(spec_tests="echo ok"))`.

**Expected:**
- `result.passed` is True, `result.exit_code` is 0.

**Assertion pseudocode:**
```
cmds = TestCommands(spec_tests="echo ok")
result = VerificationRunner(worktree).run(cmds)
ASSERT result.passed == True
ASSERT result.exit_code == 0
```

---

### TS-14-20: Verification runner returns fail for non-zero exit

**Requirement:** 14-REQ-6.3
**Type:** unit
**Description:** Verify non-zero exit code maps to passed=False.

**Preconditions:**
- Worktree with a failing test command (`exit 1`).

**Input:**
- `VerificationRunner.run(TestCommands(spec_tests="exit 1"))`.

**Expected:**
- `result.passed` is False, `result.exit_code` is 1.

**Assertion pseudocode:**
```
cmds = TestCommands(spec_tests="exit 1")
result = VerificationRunner(worktree).run(cmds)
ASSERT result.passed == False
ASSERT result.exit_code == 1
```

---

### TS-14-21: Task group commit message format

**Requirement:** 14-REQ-7.2
**Type:** integration
**Description:** Verify commit message follows conventional format.

**Preconditions:**
- Worktree with uncommitted changes.

**Input:**
- `commit_task_group(worktree, 2, "Core models")`.

**Expected:**
- Latest commit message matches `feat(<slug>): complete task group 2 — Core models`.

**Assertion pseudocode:**
```
commit_task_group(wt, 2, "Core models")
log = git_log(wt.path, n=1)
ASSERT "feat(" in log
ASSERT "task group 2" in log
ASSERT "Core models" in log
```

---

### TS-14-22: Run state persisted after node transition

**Requirement:** 14-REQ-8.1
**Type:** unit
**Description:** Verify _run.json is written after state changes.

**Preconditions:**
- Worktree directory exists.

**Input:**
- Persist state after a node transition.

**Expected:**
- `_run.json` exists in worktree root with current state.

**Assertion pseudocode:**
```
persist_state(state, worktree)
run_json = json.loads((worktree / "_run.json").read_text())
ASSERT run_json["current_phase"] == state["current_phase"]
```

---

### TS-14-23: Run state includes transition history

**Requirement:** 14-REQ-8.2
**Type:** unit
**Description:** Verify history array is maintained.

**Preconditions:**
- State with two previous transitions.

**Input:**
- Persist state.

**Expected:**
- `_run.json` has `history` array with 2 entries.

**Assertion pseudocode:**
```
state["history"] = [transition1, transition2]
persist_state(state, worktree)
run_json = json.loads((worktree / "_run.json").read_text())
ASSERT len(run_json["history"]) == 2
```

---

### TS-14-24: run_spec returns RunResult

**Requirement:** 14-REQ-9.1, 14-REQ-9.2
**Type:** integration
**Description:** Verify run_spec produces a complete RunResult.

**Preconditions:**
- Mock LLM that returns successful responses for all nodes.
- Temporary git repo with worktree.

**Input:**
- `run_spec(parsed_spec, mock_provider, worktree, config)`.

**Expected:**
- Returns `RunResult` with `success=True` and all fields populated.

**Assertion pseudocode:**
```
result = run_spec(spec, mock_provider, wt_path, config)
ASSERT result.success == True
ASSERT result.total_task_groups > 0
ASSERT result.elapsed_seconds > 0
```

---

### TS-14-25: run_campaign catches per-spec failures

**Requirement:** 14-REQ-9.3, 14-REQ-9.E1
**Type:** integration
**Description:** Verify campaign continues after a spec failure.

**Preconditions:**
- Plan with 2 specs. First spec's run_spec raises an exception.

**Input:**
- `run_campaign(plan, mock_provider, repo, config)`.

**Expected:**
- Returns 2 results: first with `success=False`, second with success.

**Assertion pseudocode:**
```
results = run_campaign(plan_2_specs, mock_provider, repo, config)
ASSERT len(results) == 2
ASSERT results[0].success == False
```

---

### TS-14-26: Drift routes back to verify_test_coverage

**Requirement:** 14-REQ-3.4
**Type:** unit
**Description:** Verify routing when verify_intent detects spec drift.

**Preconditions:**
- State with `drift_detected=True` and `attempt_count < max_attempts`.

**Input:**
- Call routing function after verify_intent.

**Expected:**
- Next node is `verify_test_coverage`.
- `attempt_count` is incremented.

**Assertion pseudocode:**
```
state = {... "drift_detected": True, "attempt_count": 1, "max_attempts": 5}
next_node = route_after_intent(state)
ASSERT next_node == "verify_test_coverage"
```

---

### TS-14-27: No drift routes to next_task_group or complete

**Requirement:** 14-REQ-3.5
**Type:** unit
**Description:** Verify routing when verify_intent confirms no drift.

**Preconditions:**
- State with `drift_detected=False`.

**Input:**
- Call routing function after verify_intent.

**Expected:**
- Next node is `next_task_group` (if more groups remain) or `complete`
  (if all groups done).

**Assertion pseudocode:**
```
state = {... "drift_detected": False, "current_task_group": 1, "total_groups": 3}
next_node = route_after_intent(state)
ASSERT next_node == "next_task_group"

state_last = {... "drift_detected": False, "current_task_group": 3, "total_groups": 3}
next_node_last = route_after_intent(state_last)
ASSERT next_node_last == "complete"
```

---

### TS-14-28: list_directory tool returns listing

**Requirement:** 14-REQ-4.4
**Type:** unit
**Description:** Verify list_directory tool lists files and directories.

**Preconditions:**
- Worktree directory with `src/main.py` and `src/lib/`.

**Input:**
- `list_directory("src")`.

**Expected:**
- Returns formatted string containing `main.py` and `lib`.

**Assertion pseudocode:**
```
(worktree / "src/main.py").write_text("hello")
(worktree / "src/lib").mkdir()
result = list_directory_tool.invoke({"path": "src"})
ASSERT "main.py" in result
ASSERT "lib" in result
```

---

### TS-14-29: File operations execute in worktree

**Requirement:** 14-REQ-5.2
**Type:** integration
**Description:** Verify all file operations target the worktree directory,
not the original repository.

**Preconditions:**
- Temporary git repo with a worktree created.

**Input:**
- Write a file via `write_file` tool, then verify location.

**Expected:**
- File exists in worktree path, not in original repo root.

**Assertion pseudocode:**
```
wt = create_worktree(repo, "test_spec", "claude-opus-4-6")
write_file_tool.invoke({"path": "new.txt", "content": "test"})
ASSERT (wt.path / "new.txt").exists()
ASSERT not (repo / "new.txt").exists()
```

---

### TS-14-30: Worktree removed after successful merge

**Requirement:** 14-REQ-5.4
**Type:** integration
**Description:** Verify worktree directory is removed and registry pruned
after successful merge.

**Preconditions:**
- Worktree with committed changes, source branch unchanged.

**Input:**
- `merge_worktree(wt_info)` then `cleanup_worktree(wt_info)`.

**Expected:**
- Worktree directory no longer exists.
- `git worktree list` does not include the worktree path.

**Assertion pseudocode:**
```
-- make changes and commit in worktree
merge_worktree(wt_info)
cleanup_worktree(wt_info)
ASSERT not wt_info.path.exists()
wt_list = git_worktree_list(repo)
ASSERT str(wt_info.path) not in wt_list
```

---

### TS-14-31: Fast-forward merge failure leaves worktree

**Requirement:** 14-REQ-5.5
**Type:** integration
**Description:** Verify that when fast-forward merge fails (branches
diverged), the worktree is left in place and failure is reported.

**Preconditions:**
- Worktree with committed changes. Source branch also has new commits
  (branches diverged).

**Input:**
- `merge_worktree(wt_info)`.

**Expected:**
- Returns failure indicator.
- Worktree directory still exists.
- Error log contains merge details.

**Assertion pseudocode:**
```
-- commit in worktree
-- commit different change on source branch (diverge)
result = merge_worktree(wt_info)
ASSERT result == False or result.success == False
ASSERT wt_info.path.exists()
```

---

### TS-14-32: Verification runner executes commands in order

**Requirement:** 14-REQ-6.1
**Type:** unit
**Description:** Verify the runner executes spec_tests after each task
group, and all_tests plus linter after the final group.

**Preconditions:**
- Worktree with test commands configured.

**Input:**
- Run verification for a non-final group, then for the final group.

**Expected:**
- Non-final: only `spec_tests` is executed.
- Final: `spec_tests`, `all_tests`, and `linter` are all executed in order.

**Assertion pseudocode:**
```
cmds = TestCommands(spec_tests="echo spec", all_tests="echo all", linter="echo lint")
result_mid = VerificationRunner(wt).run(cmds, is_final_group=False)
ASSERT result_mid.commands_run == ["spec_tests"]

result_final = VerificationRunner(wt).run(cmds, is_final_group=True)
ASSERT result_final.commands_run == ["spec_tests", "all_tests", "linter"]
```

---

### TS-14-33: Verification runner enforces configurable timeout

**Requirement:** 14-REQ-6.4
**Type:** unit
**Description:** Verify the runner enforces a configurable per-command
timeout and returns a timeout failure when exceeded.

**Preconditions:**
- Worktree with a slow test command.

**Input:**
- `VerificationRunner.run(cmds, timeout=1)` with a command that sleeps.

**Expected:**
- Returns fail result with timeout indication.

**Assertion pseudocode:**
```
cmds = TestCommands(spec_tests="sleep 60")
result = VerificationRunner(wt).run(cmds, timeout=1)
ASSERT result.passed == False
ASSERT "timeout" in result.stderr.lower() or result.timed_out == True
```

---

### TS-14-34: Task groups iterated in order

**Requirement:** 14-REQ-7.1
**Type:** unit
**Description:** Verify the system iterates through task groups in the
order defined in tasks.json, starting with group 1.

**Preconditions:**
- Parsed spec with 3 task groups.

**Input:**
- Simulate graph execution tracking group transitions.

**Expected:**
- Groups are processed in order: 1, 2, 3.

**Assertion pseudocode:**
```
spec = parsed_spec_with_groups([1, 2, 3])
groups_visited = simulate_group_iteration(spec)
ASSERT groups_visited == [1, 2, 3]
```

---

### TS-14-35: Task group advances counter and resets attempts

**Requirement:** 14-REQ-7.3
**Type:** unit
**Description:** Verify that when a task group completes, the system
advances current_task_group and resets attempt_count to 0.

**Preconditions:**
- State with `current_task_group=2`, `attempt_count=3`.

**Input:**
- Call `next_task_group(state)`.

**Expected:**
- `current_task_group` = 3, `attempt_count` = 0.

**Assertion pseudocode:**
```
state = {... "current_task_group": 2, "attempt_count": 3}
new_state = next_task_group(state)
ASSERT new_state["current_task_group"] == 3
ASSERT new_state["attempt_count"] == 0
```

---

### TS-14-36: All groups complete sets phase to complete

**Requirement:** 14-REQ-7.4
**Type:** unit
**Description:** Verify that when all task groups are complete and
verified, the system sets current_phase to "complete".

**Preconditions:**
- State with `current_task_group` equal to total groups.

**Input:**
- Call routing after final task group verification passes.

**Expected:**
- `current_phase` = `"complete"`.

**Assertion pseudocode:**
```
state = {... "current_task_group": 3, "total_groups": 3, "drift_detected": False}
next_node = route_after_intent(state)
ASSERT next_node == "complete"
-- or equivalently:
final_state = complete_node(state)
ASSERT final_state["current_phase"] == "complete"
```

---

### TS-14-37: Run state written atomically

**Requirement:** 14-REQ-8.3
**Type:** unit
**Description:** Verify _run.json is written atomically via write-to-temp
then rename, preventing corruption on crash.

**Preconditions:**
- Worktree directory exists.

**Input:**
- Persist state and verify atomic write behavior.

**Expected:**
- No partial writes observable. If the write is interrupted, the
  previous _run.json remains intact.

**Assertion pseudocode:**
```
-- Write initial state
persist_state(state_v1, worktree)
initial = (worktree / "_run.json").read_text()

-- Mock os.rename to fail, simulating crash during atomic write
with mock.patch("os.rename", side_effect=OSError):
    try:
        persist_state(state_v2, worktree)
    except OSError:
        pass

-- Original file should be unchanged (atomic guarantee)
ASSERT (worktree / "_run.json").read_text() == initial
```

---

## Property Test Cases

### TS-14-P1: Monotonic task group progress

**Property:** Property 1 from design.md
**Validates:** 14-REQ-7.1, 14-REQ-7.3
**Type:** property
**Description:** Task groups never decrease during execution.

**For any:** Sequence of state transitions from a mocked graph execution
**Invariant:** For consecutive transitions where phase is `next_task_group`,
the task group number strictly increases.

**Assertion pseudocode:**
```
FOR ANY mock_execution IN graph_executions(min_groups=2, max_groups=5):
    groups = [t.task_group for t in mock_execution.transitions if t.phase == "next_task_group"]
    ASSERT groups == sorted(groups)
    ASSERT len(groups) == len(set(groups))  -- no duplicates
```

---

### TS-14-P2: Retry never exceeds max_attempts

**Property:** Property 2 from design.md
**Validates:** 14-REQ-3.2, 14-REQ-3.6
**Type:** property
**Description:** Attempt count is bounded by max_attempts.

**For any:** max_attempts in range(1, 10), sequence of test failures
**Invariant:** The number of implement calls for any single task group
does not exceed max_attempts.

**Assertion pseudocode:**
```
FOR ANY max_attempts IN integers(1, 10):
    state = create_state(max_attempts=max_attempts)
    implement_calls = simulate_failing_loop(state)
    ASSERT implement_calls <= max_attempts
```

---

### TS-14-P3: Path containment

**Property:** Property 3 from design.md
**Validates:** 14-REQ-4.5
**Type:** property
**Description:** All tool paths resolve within the worktree.

**For any:** path string containing `..`, absolute paths, or symlink
components
**Invariant:** The tool rejects the path or resolves it within the
worktree boundary.

**Assertion pseudocode:**
```
FOR ANY path IN paths_with_traversal_attempts():
    result = read_file_tool.invoke({"path": path})
    resolved = resolve_path(worktree, path)
    ASSERT resolved.is_relative_to(worktree) OR "error" in result
```

---

### TS-14-P4: Worktree isolation

**Property:** Property 4 from design.md
**Validates:** 14-REQ-5.2
**Type:** property
**Description:** All file modifications occur within the worktree.

**For any:** Set of file write operations during spec execution
**Invariant:** No file outside the worktree directory is modified.

**Assertion pseudocode:**
```
FOR ANY file_writes IN write_operations(min_count=1, max_count=10):
    snapshot = hash_directory(repo_root)
    execute_writes_in_worktree(file_writes, worktree)
    ASSERT hash_directory(repo_root) == snapshot
```

---

### TS-14-P5: Commit after success

**Property:** Property 5 from design.md
**Validates:** 14-REQ-7.2
**Type:** property
**Description:** Each completed task group produces exactly one commit.

**For any:** Number of task groups in range(1, 5), all passing
**Invariant:** Commit count equals completed task group count.

**Assertion pseudocode:**
```
FOR ANY n_groups IN integers(1, 5):
    result = simulate_successful_run(n_groups)
    ASSERT git_log_count(worktree) == n_groups
```

---

### TS-14-P6: State persistence completeness

**Property:** Property 6 from design.md
**Validates:** 14-REQ-8.1
**Type:** property
**Description:** After every node transition, _run.json reflects current state.

**For any:** Sequence of node transitions
**Invariant:** _run.json always matches current phase and task group.

**Assertion pseudocode:**
```
FOR ANY transitions IN node_sequences(min_len=1, max_len=10):
    FOR EACH t IN transitions:
        apply_transition(state, t)
        persist_state(state, worktree)
        saved = json.loads((worktree / "_run.json").read_text())
        ASSERT saved["current_phase"] == state["current_phase"]
```

---

### TS-14-P7: Verification exit code semantics

**Property:** Property 7 from design.md
**Validates:** 14-REQ-6.3
**Type:** property
**Description:** Exit code 0 = pass, non-zero = fail.

**For any:** exit code in range(0, 128)
**Invariant:** passed=True iff exit_code == 0.

**Assertion pseudocode:**
```
FOR ANY exit_code IN integers(0, 128):
    result = VerificationResult(exit_code=exit_code, ...)
    IF exit_code == 0:
        ASSERT result.passed == True
    ELSE:
        ASSERT result.passed == False
```

## Edge Case Tests

### TS-14-E8: Unhandled exception in run_spec caught by campaign

**Requirement:** 14-REQ-9.E1
**Type:** integration
**Description:** Verify run_campaign catches unhandled exceptions per spec.

**Preconditions:**
- Plan with 2 specs. First raises RuntimeError in run_spec.

**Input:**
- `run_campaign(plan, provider, repo, config)`.

**Expected:**
- Returns 2 results. First has success=False with error details.
- Second spec still executes.

**Assertion pseudocode:**
```
results = run_campaign(plan_2_specs, exploding_provider, repo, config)
ASSERT len(results) == 2
ASSERT results[0].success == False
ASSERT "error" in results[0].halt_reason.lower()
```

---

### TS-14-E1: LLM empty response triggers retry

**Requirement:** 14-REQ-2.E1
**Type:** unit
**Description:** Verify empty LLM response increments attempt count.

**Preconditions:**
- Mock LLM returns empty string.

**Input:**
- Call any LLM-using node.

**Expected:**
- `attempt_count` incremented.

**Assertion pseudocode:**
```
mock_llm.return_value = ""
new_state = implement({... "attempt_count": 0}, mock_llm)
ASSERT new_state["attempt_count"] == 1
```

---

### TS-14-E2: Halted state skips node execution

**Requirement:** 14-REQ-3.E1
**Type:** unit
**Description:** Verify nodes pass through when halted.

**Preconditions:**
- State with `halted=True`.

**Input:**
- Call `implement(halted_state)`.

**Expected:**
- State unchanged.

**Assertion pseudocode:**
```
halted_state = {... "halted": True}
new_state = implement(halted_state, mock_llm)
ASSERT new_state == halted_state
ASSERT not mock_llm.invoke.called
```

---

### TS-14-E3: Command timeout returns failure

**Requirement:** 14-REQ-4.E1
**Type:** unit
**Description:** Verify command timeout produces error result.

**Preconditions:**
- Tool configured with 1-second timeout.

**Input:**
- `run_command("sleep 60")`.

**Expected:**
- Returns error message mentioning timeout.

**Assertion pseudocode:**
```
result = run_command_tool.invoke({"command": "sleep 60"}, timeout=1)
ASSERT "timeout" in result.lower()
```

---

### TS-14-E4: Symlink write rejected

**Requirement:** 14-REQ-4.E3
**Type:** unit
**Description:** Verify writing to symlinks is blocked.

**Preconditions:**
- Worktree contains symlink `link.txt` → `/tmp/target`.

**Input:**
- `write_file("link.txt", "content")`.

**Expected:**
- Returns security error.

**Assertion pseudocode:**
```
create_symlink(worktree / "link.txt", "/tmp/target")
result = write_file_tool.invoke({"path": "link.txt", "content": "x"})
ASSERT "error" in result.lower()
```

---

### TS-14-E5: Stale worktree removed before creation

**Requirement:** 14-REQ-5.E1
**Type:** integration
**Description:** Verify stale worktree is cleaned up.

**Preconditions:**
- Stale worktree directory exists from a previous run.

**Input:**
- `create_worktree(repo, "base_app", "claude-opus-4-6")`.

**Expected:**
- New worktree created successfully (stale one removed).

**Assertion pseudocode:**
```
stale_path = repo / ".coder/worktrees/base_app"
stale_path.mkdir(parents=True)
wt = create_worktree(repo, "base_app", "claude-opus-4-6")
ASSERT wt.path.exists()
```

---

### TS-14-E6: Empty test command skipped

**Requirement:** 14-REQ-6.E1
**Type:** unit
**Description:** Verify empty test commands are skipped.

**Preconditions:**
- TestCommands with empty spec_tests.

**Input:**
- `VerificationRunner.run(TestCommands(spec_tests=""))`.

**Expected:**
- Skips command, returns pass (no test to fail).
- Warning logged.

**Assertion pseudocode:**
```
with capture_logs() as logs:
    result = VerificationRunner(wt).run(TestCommands(spec_tests=""))
ASSERT result.passed == True
ASSERT any("skip" in log for log in logs)
```

---

### TS-14-E7: Commit failure does not crash

**Requirement:** 14-REQ-7.E1
**Type:** integration
**Description:** Verify commit failure is handled gracefully.

**Preconditions:**
- Worktree with no changes to commit.

**Input:**
- `commit_task_group(worktree, 1, "Tests")`.

**Expected:**
- Does not raise. Warning logged.

**Assertion pseudocode:**
```
with capture_logs() as logs:
    commit_task_group(clean_worktree, 1, "Tests")
ASSERT any("warning" in log or "nothing" in log for log in logs)
```

---

### TS-14-E9: Missing state field uses sensible default

**Requirement:** 14-REQ-1.E1
**Type:** unit
**Description:** Verify that when a node reads a state field that is
missing, it uses a sensible default rather than raising a KeyError.

**Preconditions:**
- State dictionary with some fields intentionally omitted.

**Input:**
- Call a node function with an incomplete state.

**Expected:**
- No KeyError raised. Missing str fields default to empty string,
  int fields to 0, bool fields to False.

**Assertion pseudocode:**
```
incomplete_state = {"current_phase": "implement", "messages": []}
-- omit attempt_count, halted, spec_context, etc.
new_state = implement(incomplete_state, mock_llm)
-- should not raise KeyError
ASSERT new_state["attempt_count"] >= 0
ASSERT new_state["halted"] in (True, False)
```

---

### TS-14-E10: Binary file read returns error

**Requirement:** 14-REQ-4.E2
**Type:** unit
**Description:** Verify that read_file returns an error message when
called with a path to a binary file.

**Preconditions:**
- Worktree contains a binary file (e.g., a small PNG or compiled object).

**Input:**
- `read_file("image.png")`.

**Expected:**
- Returns error message indicating the file is binary.

**Assertion pseudocode:**
```
(worktree / "image.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
result = read_file_tool.invoke({"path": "image.png"})
ASSERT "binary" in result.lower() or "error" in result.lower()
```

---

### TS-14-E11: Worktree creation failure raises WorktreeError

**Requirement:** 14-REQ-5.E2
**Type:** integration
**Description:** Verify that when git worktree creation fails, the system
raises a WorktreeError with the git error output.

**Preconditions:**
- Git repository in a state where worktree creation will fail (e.g.,
  branch name already exists as a checked-out worktree).

**Input:**
- `create_worktree(repo, "conflict_spec", "claude-opus-4-6")` when the
  branch is already checked out elsewhere.

**Expected:**
- Raises `WorktreeError` with message containing git error output.

**Assertion pseudocode:**
```
-- Create first worktree (succeeds)
create_worktree(repo, "conflict_spec", "claude-opus-4-6")
-- Try to create second worktree with same branch (fails)
WITH ASSERT_RAISES(WorktreeError) as exc:
    create_worktree(repo, "conflict_spec", "claude-opus-4-6", force_new_branch=False)
ASSERT "already" in str(exc) or "fatal" in str(exc)
```

---

### TS-14-E12: Command binary not found returns fail result

**Requirement:** 14-REQ-6.E2
**Type:** unit
**Description:** Verify that when a test command binary is not found,
the runner returns a fail result with the error message rather than
crashing.

**Preconditions:**
- Test commands referencing a non-existent binary.

**Input:**
- `VerificationRunner.run(TestCommands(spec_tests="nonexistent_binary_xyz --test"))`.

**Expected:**
- Returns fail result (not an exception).
- Error message mentions the missing command.

**Assertion pseudocode:**
```
cmds = TestCommands(spec_tests="nonexistent_binary_xyz --test")
result = VerificationRunner(wt).run(cmds)
ASSERT result.passed == False
ASSERT "not found" in result.stderr.lower() or result.exit_code != 0
```

---

### TS-14-E13: Run state write failure handled gracefully

**Requirement:** 14-REQ-8.E1
**Type:** unit
**Description:** Verify that when writing _run.json fails (e.g., disk
full or permission denied), the system logs a warning and continues
execution rather than crashing.

**Preconditions:**
- Worktree directory with read-only permissions (or mocked write failure).

**Input:**
- `persist_state(state, worktree)` when write will fail.

**Expected:**
- Does not raise an exception.
- Warning is logged.

**Assertion pseudocode:**
```
with mock.patch("builtins.open", side_effect=OSError("disk full")):
    with capture_logs() as logs:
        persist_state(state, worktree)  -- should not raise
ASSERT any("warning" in log or "disk" in log for log in logs)
```

---

## Integration Smoke Tests

### TS-14-SMOKE-1: Full graph execution with mock LLM

**Execution Path:** Path 1 from design.md
**Description:** Verify the complete LangGraph workflow executes from
understand_spec through completion with a mock LLM.

**Setup:** Mock LLM returns appropriate responses for each node. Real
worktree in a temporary git repo. Spec pack with one task group.

**Trigger:** `run_spec(parsed_spec, mock_provider, worktree, config)`

**Expected side effects:**
- Returns RunResult with `success=True`.
- Files modified in worktree.
- `_run.json` exists with `current_phase="complete"`.

**Must NOT satisfy with:** Mocking the graph execution itself — the real
LangGraph must run node-by-node.

**Assertion pseudocode:**
```
result = run_spec(spec, mock_provider, wt_path, config)
ASSERT result.success == True
run_json = json.loads((wt_path / "_run.json").read_text())
ASSERT run_json["current_phase"] == "complete"
```

---

### TS-14-SMOKE-2: Worktree lifecycle end-to-end

**Execution Path:** Path 2 from design.md
**Description:** Verify create → commit → merge → cleanup worktree cycle.

**Setup:** Temporary git repo with initial commit.

**Trigger:** Create worktree, write a file, commit, merge, cleanup.

**Expected side effects:**
- After merge, source branch contains the new file.
- Worktree directory no longer exists.

**Must NOT satisfy with:** Mocking git commands — real git operations must
execute.

**Assertion pseudocode:**
```
wt = create_worktree(repo, "test_spec", "claude-opus-4-6")
write_file(wt.path / "new.txt", "content")
git_add_commit(wt.path, "feat: add file")
merge_worktree(wt)
cleanup_worktree(wt)
ASSERT not wt.path.exists()
ASSERT (repo / "new.txt").read_text() == "content"
```

---

### TS-14-SMOKE-3: Campaign runs multiple specs

**Execution Path:** Path 3 from design.md
**Description:** Verify run_campaign iterates over specs in plan order.

**Setup:** Execution plan with 2 specs. Mock LLM. Temporary git repo.

**Trigger:** `run_campaign(plan, mock_provider, repo, config)`

**Expected side effects:**
- Returns 2 RunResult objects.
- Each spec's worktree was created and merged.

**Must NOT satisfy with:** Mocking run_spec — the real function must execute
for each spec.

**Assertion pseudocode:**
```
results = run_campaign(plan_2_specs, mock_provider, repo, config)
ASSERT len(results) == 2
```

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 14-REQ-1.1 | TS-14-1 | unit |
| 14-REQ-1.2 | TS-14-1 | unit |
| 14-REQ-1.E1 | TS-14-1 | unit |
| 14-REQ-2.1 | TS-14-2 | unit |
| 14-REQ-2.2 | TS-14-3 | unit |
| 14-REQ-2.3 | TS-14-4 | unit |
| 14-REQ-2.4 | TS-14-5 | unit |
| 14-REQ-2.5 | TS-14-6 | unit |
| 14-REQ-2.6 | TS-14-7 | unit |
| 14-REQ-2.7 | TS-14-8 | unit |
| 14-REQ-2.E1 | TS-14-E1 | unit |
| 14-REQ-3.1 | TS-14-9 | unit |
| 14-REQ-3.2 | TS-14-10 | unit |
| 14-REQ-3.3 | TS-14-11 | unit |
| 14-REQ-3.6 | TS-14-12 | unit |
| 14-REQ-3.E1 | TS-14-E2 | unit |
| 14-REQ-4.1 | TS-14-13 | unit |
| 14-REQ-4.2 | TS-14-14 | unit |
| 14-REQ-4.3 | TS-14-15 | unit |
| 14-REQ-4.5 | TS-14-16 | unit |
| 14-REQ-4.E1 | TS-14-E3 | unit |
| 14-REQ-4.E3 | TS-14-E4 | unit |
| 14-REQ-5.1 | TS-14-17 | integration |
| 14-REQ-5.3 | TS-14-18 | integration |
| 14-REQ-5.E1 | TS-14-E5 | integration |
| 14-REQ-6.2 | TS-14-19 | unit |
| 14-REQ-6.3 | TS-14-20 | unit |
| 14-REQ-6.E1 | TS-14-E6 | unit |
| 14-REQ-7.2 | TS-14-21 | integration |
| 14-REQ-7.E1 | TS-14-E7 | integration |
| 14-REQ-8.1 | TS-14-22 | unit |
| 14-REQ-8.2 | TS-14-23 | unit |
| 14-REQ-9.1 | TS-14-24 | integration |
| 14-REQ-9.2 | TS-14-24 | integration |
| 14-REQ-9.3 | TS-14-25 | integration |
| 14-REQ-9.E1 | TS-14-25 | integration |
| 14-REQ-9.E1 | TS-14-E8 | integration |
| Property 1 | TS-14-P1 | property |
| Property 2 | TS-14-P2 | property |
| Property 3 | TS-14-P3 | property |
| Property 4 | TS-14-P4 | property |
| Property 5 | TS-14-P5 | property |
| Property 6 | TS-14-P6 | property |
| Property 7 | TS-14-P7 | property |
| Path 1 | TS-14-SMOKE-1 | integration |
| Path 2 | TS-14-SMOKE-2 | integration |
| Path 3 | TS-14-SMOKE-3 | integration |
| 14-REQ-1.E1 | TS-14-E9 | unit |
| 14-REQ-3.4 | TS-14-26 | unit |
| 14-REQ-3.5 | TS-14-27 | unit |
| 14-REQ-3.E1 | TS-14-E2 | unit |
| 14-REQ-4.4 | TS-14-28 | unit |
| 14-REQ-4.E2 | TS-14-E10 | unit |
| 14-REQ-5.2 | TS-14-29 | integration |
| 14-REQ-5.4 | TS-14-30 | integration |
| 14-REQ-5.5 | TS-14-31 | integration |
| 14-REQ-5.E2 | TS-14-E11 | integration |
| 14-REQ-6.1 | TS-14-32 | unit |
| 14-REQ-6.4 | TS-14-33 | unit |
| 14-REQ-6.E2 | TS-14-E12 | unit |
| 14-REQ-7.1 | TS-14-34 | unit |
| 14-REQ-7.3 | TS-14-35 | unit |
| 14-REQ-7.4 | TS-14-36 | unit |
| 14-REQ-8.3 | TS-14-37 | unit |
| 14-REQ-8.E1 | TS-14-E13 | unit |
