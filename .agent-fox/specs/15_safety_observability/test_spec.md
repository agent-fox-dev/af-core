# Test Specification: Safety & Observability

## Overview

Tests cover circuit breaker enforcement, token tracking across providers,
post-mortem generation, console logging, graceful shutdown, and run
summary. Uses mocked LLM responses to simulate token metadata from each
provider type.

## Test Cases

### TS-15-1: Circuit breaker trips on max attempts

**Requirement:** 15-REQ-1.1
**Type:** unit
**Description:** Verify halt on attempt limit.

**Preconditions:**
- SafetyConfig with `max_attempts_per_task=3`.

**Input:**
- State with `attempt_count=3`.
- `CircuitBreaker.check(state, tracker)`.

**Expected:**
- Returns `CheckResult(halted=True, reason="...")`.

**Assertion pseudocode:**
```
cb = CircuitBreaker(SafetyConfig(max_attempts_per_task=3))
state = {"attempt_count": 3, ...}
result = cb.check(state, tracker)
ASSERT result.halted == True
ASSERT "attempts" in result.reason
```

---

### TS-15-2: Circuit breaker trips on wall time

**Requirement:** 15-REQ-1.2
**Type:** unit
**Description:** Verify halt on time limit.

**Preconditions:**
- SafetyConfig with `max_wall_time_seconds=60`.

**Input:**
- State with start_time 120 seconds ago.
- `CircuitBreaker.check(state, tracker)`.

**Expected:**
- Returns halted with time-related reason.

**Assertion pseudocode:**
```
cb = CircuitBreaker(SafetyConfig(max_wall_time_seconds=60), start_time=time.time() - 120)
result = cb.check(state, tracker)
ASSERT result.halted == True
ASSERT "time" in result.reason
```

---

### TS-15-3: Circuit breaker trips on max tokens

**Requirement:** 15-REQ-1.3
**Type:** unit
**Description:** Verify halt on token limit.

**Preconditions:**
- SafetyConfig with `max_tokens=1000`.

**Input:**
- TokenTracker with `total_tokens=1500`.
- `CircuitBreaker.check(state, tracker)`.

**Expected:**
- Returns halted with token-related reason.

**Assertion pseudocode:**
```
cb = CircuitBreaker(SafetyConfig(max_tokens=1000))
tracker = TokenTracker()
tracker._input_tokens = 1000
tracker._output_tokens = 500
result = cb.check(state, tracker)
ASSERT result.halted == True
ASSERT "token" in result.reason
```

---

### TS-15-4: Circuit breaker passes when within limits

**Requirement:** 15-REQ-1.4
**Type:** unit
**Description:** Verify no halt when all limits OK.

**Preconditions:**
- State with `attempt_count=1`, 10 seconds elapsed, 100 tokens used.

**Input:**
- `CircuitBreaker.check(state, tracker)`.

**Expected:**
- Returns `CheckResult(halted=False)`.

**Assertion pseudocode:**
```
cb = CircuitBreaker(SafetyConfig(max_attempts_per_task=5, max_wall_time_seconds=1800, max_tokens=2000000))
result = cb.check(state, tracker)
ASSERT result.halted == False
```

---

### TS-15-5: TokenTracker accumulates Anthropic tokens

**Requirement:** 15-REQ-2.1, 15-REQ-2.2
**Type:** unit
**Description:** Verify token tracking from Anthropic responses.

**Preconditions:**
- Mock LLM response with `usage: {input_tokens: 100, output_tokens: 50}`.

**Input:**
- `tracker.on_llm_end(response)`.

**Expected:**
- `tracker.input_tokens` = 100, `tracker.output_tokens` = 50.

**Assertion pseudocode:**
```
tracker = TokenTracker()
response = mock_anthropic_response(input_tokens=100, output_tokens=50)
tracker.on_llm_end(response)
ASSERT tracker.input_tokens == 100
ASSERT tracker.output_tokens == 50
```

---

### TS-15-6: TokenTracker accumulates Google tokens

**Requirement:** 15-REQ-2.2
**Type:** unit
**Description:** Verify token tracking from Google responses.

**Preconditions:**
- Mock response with Google token fields.

**Input:**
- `tracker.on_llm_end(google_response)`.

**Expected:**
- Tokens normalized to input_tokens/output_tokens.

**Assertion pseudocode:**
```
tracker = TokenTracker()
response = mock_google_response(prompt_token_count=200, candidates_token_count=80)
tracker.on_llm_end(response)
ASSERT tracker.input_tokens == 200
ASSERT tracker.output_tokens == 80
```

---

### TS-15-7: TokenTracker total_tokens property

**Requirement:** 15-REQ-2.3
**Type:** unit
**Description:** Verify total_tokens is input + output.

**Preconditions:**
- Tracker with accumulated tokens.

**Input:**
- Access `tracker.total_tokens`.

**Expected:**
- Returns sum of input and output tokens.

**Assertion pseudocode:**
```
tracker = TokenTracker()
tracker.on_llm_end(response_with_100_input_50_output)
ASSERT tracker.total_tokens == 150
```

---

### TS-15-8: TokenTracker to_dict returns breakdown

**Requirement:** 15-REQ-2.3
**Type:** unit
**Description:** Verify to_dict returns structured data.

**Preconditions:**
- Tracker with tokens.

**Input:**
- `tracker.to_dict()`.

**Expected:**
- Dict with `input_tokens`, `output_tokens`, `total_tokens`, `call_count`.

**Assertion pseudocode:**
```
d = tracker.to_dict()
ASSERT "input_tokens" in d
ASSERT "output_tokens" in d
ASSERT "total_tokens" in d
ASSERT d["total_tokens"] == d["input_tokens"] + d["output_tokens"]
```

---

### TS-15-9: Post-mortem contains required sections

**Requirement:** 15-REQ-3.2
**Type:** unit
**Description:** Verify all post-mortem sections are present.

**Preconditions:**
- State with halt_reason, history, test_results.

**Input:**
- `generate_postmortem(state, worktree, tracker)`.

**Expected:**
- Generated markdown contains all required sections.

**Assertion pseudocode:**
```
path = generate_postmortem(halted_state, tmp_dir, tracker)
content = path.read_text()
ASSERT "## Summary" in content
ASSERT "## Halt Reason" in content
ASSERT "## Execution Context" in content
ASSERT "## Attempt History" in content
ASSERT "## Last Test Output" in content
ASSERT "## Token Usage" in content
ASSERT "## Recommendations" in content
```

---

### TS-15-10: Post-mortem written to worktree

**Requirement:** 15-REQ-3.1
**Type:** unit
**Description:** Verify post-mortem file location.

**Preconditions:**
- Worktree directory exists.

**Input:**
- `generate_postmortem(state, worktree, tracker)`.

**Expected:**
- `_postmortem.md` exists in worktree.

**Assertion pseudocode:**
```
path = generate_postmortem(state, tmp_worktree, tracker)
ASSERT path == tmp_worktree / "_postmortem.md"
ASSERT path.exists()
```

---

### TS-15-11: Console logger shows phase transitions

**Requirement:** 15-REQ-4.1, 15-REQ-4.5
**Type:** unit
**Description:** Verify console output includes phase and progress.

**Preconditions:**
- ConsoleLogger with captured output.

**Input:**
- `logger.log_transition("implement", task_group=2, attempt=1, max_attempts=5)`.

**Expected:**
- Output contains "implement", "2", "1/5" or similar.

**Assertion pseudocode:**
```
with capture_output() as out:
    logger.log_transition("implement", 2, 1, 5)
ASSERT "implement" in out
ASSERT "2" in out
```

---

### TS-15-12: Console logger shows test results

**Requirement:** 15-REQ-4.2
**Type:** unit
**Description:** Verify test results displayed in console.

**Preconditions:**
- ConsoleLogger with captured output.

**Input:**
- `logger.log_test_result(VerificationResult(passed=True, ...))`.

**Expected:**
- Output contains pass indicator.

**Assertion pseudocode:**
```
with capture_output() as out:
    logger.log_test_result(VerificationResult(passed=True, exit_code=0, stdout="3 passed"))
ASSERT "pass" in out.lower() or "✓" in out
```

---

### TS-15-13: Graceful shutdown preserves state

**Requirement:** 15-REQ-5.2
**Type:** unit
**Description:** Verify state is persisted during shutdown.

**Preconditions:**
- Worktree with ongoing execution state.

**Input:**
- Trigger graceful shutdown.

**Expected:**
- `_run.json` exists with final state.
- `_postmortem.md` exists.

**Assertion pseudocode:**
```
perform_graceful_shutdown(state, worktree, tracker)
ASSERT (worktree / "_run.json").exists()
ASSERT (worktree / "_postmortem.md").exists()
```

---

### TS-15-14: Run summary contains required fields

**Requirement:** 15-REQ-6.2
**Type:** unit
**Description:** Verify run summary has all expected fields.

**Preconditions:**
- Completed execution state.

**Input:**
- `write_run_summary(state, worktree, tracker)`.

**Expected:**
- Summary contains spec name, model, groups, tokens, time, status.

**Assertion pseudocode:**
```
path = write_run_summary(state, tmp_worktree, tracker)
content = path.read_text()
ASSERT "spec" in content.lower()
ASSERT "model" in content.lower()
ASSERT "token" in content.lower()
```

---

### TS-15-15: Safety config extends CoderConfig

**Requirement:** 15-REQ-7.1, 15-REQ-7.2
**Type:** unit
**Description:** Verify SafetyConfig is part of CoderConfig.

**Preconditions:**
- `.coder.yaml` with safety section.

**Input:**
- `load_config()`.

**Expected:**
- `config.safety.max_attempts_per_task` equals configured value.

**Assertion pseudocode:**
```
write_file(tmp / ".coder.yaml", "safety:\n  max_attempts_per_task: 3\n")
config = load_config(project_dir=tmp)
ASSERT config.safety.max_attempts_per_task == 3
```

## Property Test Cases

### TS-15-P1: Halt guarantee

**Property:** Property 1 from design.md
**Validates:** 15-REQ-1.4, 15-REQ-5.1
**Type:** property
**Description:** Once a limit is breached, no further workflow nodes execute.

**For any:** max_attempts in range(1, 10), sequence of failing iterations
**Invariant:** The number of implement calls after halt is zero.

**Assertion pseudocode:**
```
FOR ANY max_attempts IN integers(1, 10):
    cb = CircuitBreaker(SafetyConfig(max_attempts_per_task=max_attempts))
    post_halt_calls = simulate_with_halt(cb, always_fail=True)
    ASSERT post_halt_calls == 0
```

---

### TS-15-P2: Token monotonicity

**Property:** Property 2 from design.md
**Validates:** 15-REQ-2.1, 15-REQ-2.3
**Type:** property
**Description:** Token counts never decrease.

**For any:** Sequence of 1-20 LLM responses with random positive token counts
**Invariant:** After each on_llm_end call, total_tokens >= previous total.

**Assertion pseudocode:**
```
FOR ANY token_sequence IN lists(tuples(integers(0, 10000), integers(0, 10000))):
    tracker = TokenTracker()
    prev = 0
    FOR EACH (inp, out) IN token_sequence:
        tracker.on_llm_end(mock_response(inp, out))
        ASSERT tracker.total_tokens >= prev
        prev = tracker.total_tokens
```

---

### TS-15-P3: Post-mortem section completeness

**Property:** Property 3 from design.md
**Validates:** 15-REQ-3.2
**Type:** property
**Description:** Every generated post-mortem has all required sections.

**For any:** Halt reason from {attempts, time, tokens}, random state values
**Invariant:** The generated markdown contains all 7 required section headers.

**Assertion pseudocode:**
```
REQUIRED = ["## Summary", "## Halt Reason", "## Execution Context",
            "## Attempt History", "## Last Test Output", "## Token Usage",
            "## Recommendations"]
FOR ANY halt_reason IN sampled_from(["attempts", "time", "tokens"]):
    state = random_halted_state(halt_reason)
    path = generate_postmortem(state, tmp_dir, tracker)
    content = path.read_text()
    FOR EACH section IN REQUIRED:
        ASSERT section in content
```

---

### TS-15-P4: Configuration defaults are safe

**Property:** Property 4 from design.md
**Validates:** 15-REQ-1.1, 15-REQ-1.2, 15-REQ-1.3, 15-REQ-1.E2
**Type:** property
**Description:** Default safety config values do not cause immediate halt.

**For any:** Default SafetyConfig (no overrides)
**Invariant:** CircuitBreaker.check returns halted=False for a fresh state.

**Assertion pseudocode:**
```
cb = CircuitBreaker(SafetyConfig())  -- all defaults
state = create_initial_state()
tracker = TokenTracker()  -- zero tokens
result = cb.check(state, tracker)
ASSERT result.halted == False
```

## Edge Case Tests

### TS-15-E1: Zero limit raises ConfigError

**Requirement:** 15-REQ-1.E1
**Type:** unit
**Description:** Verify zero/negative limits are rejected at startup.

**Preconditions:**
- SafetyConfig with `max_attempts_per_task=0`.

**Input:**
- Create CircuitBreaker.

**Expected:**
- Raises `ConfigError`.

**Assertion pseudocode:**
```
ASSERT_RAISES ConfigError:
    CircuitBreaker(SafetyConfig(max_attempts_per_task=0))
```

---

### TS-15-E2: Null limit means unlimited

**Requirement:** 15-REQ-1.E2
**Type:** unit
**Description:** Verify null limits are not enforced.

**Preconditions:**
- SafetyConfig with `max_tokens=None`.

**Input:**
- State with very high token count (999,999,999).
- `CircuitBreaker.check(state, tracker)`.

**Expected:**
- Returns `halted=False` (unlimited).

**Assertion pseudocode:**
```
cb = CircuitBreaker(SafetyConfig(max_tokens=None))
tracker = TokenTracker()
tracker._input_tokens = 999999999
result = cb.check(state, tracker)
ASSERT result.halted == False
```

---

### TS-15-E3: Missing token metadata warns

**Requirement:** 15-REQ-2.E1
**Type:** unit
**Description:** Verify warning when tokens not reported.

**Preconditions:**
- Response with no token usage metadata.

**Input:**
- `tracker.on_llm_end(response_no_metadata)`.

**Expected:**
- Warning logged. No crash. Tokens remain unchanged.

**Assertion pseudocode:**
```
tracker = TokenTracker()
with capture_logs() as logs:
    tracker.on_llm_end(empty_metadata_response)
ASSERT tracker.total_tokens == 0
ASSERT any("warning" in log or "token" in log for log in logs)
```

---

### TS-15-E4: Post-mortem to cwd when no worktree

**Requirement:** 15-REQ-3.E1
**Type:** unit
**Description:** Verify fallback to cwd for post-mortem.

**Preconditions:**
- Worktree path does not exist.

**Input:**
- `generate_postmortem(state, nonexistent_path, tracker)`.

**Expected:**
- Post-mortem written to current working directory.

**Assertion pseudocode:**
```
path = generate_postmortem(state, Path("/nonexistent"), tracker)
ASSERT path.parent == Path.cwd()
```

---

### TS-15-E5: Non-TTY falls back to plain text

**Requirement:** 15-REQ-4.E1
**Type:** unit
**Description:** Verify color-free output in non-TTY mode.

**Preconditions:**
- Console created with `force_terminal=False`.

**Input:**
- `logger.log_transition("implement", 1, 1, 5)`.

**Expected:**
- Output contains no ANSI escape codes.

**Assertion pseudocode:**
```
logger = ConsoleLogger(force_terminal=False)
with capture_output() as out:
    logger.log_transition("implement", 1, 1, 5)
ASSERT "\033[" not in out
```

---

### TS-15-E6: SIGINT triggers graceful shutdown

**Requirement:** 15-REQ-5.E1
**Type:** integration
**Description:** Verify Ctrl+C is caught and handled.

**Preconditions:**
- Running execution loop.

**Input:**
- Send SIGINT signal.

**Expected:**
- Shutdown sequence completes. State and post-mortem written.

**Assertion pseudocode:**
```
-- Start execution in a thread
-- Send SIGINT after brief delay
-- Verify _run.json and _postmortem.md exist
```

---

### TS-15-16: TokenTracker registered as callback on LLM invocations

**Requirement:** 15-REQ-2.4
**Type:** unit
**Description:** Verify the TokenTracker is registered as a callback when
invoking the LLM provider.

**Preconditions:**
- Mock LLM provider with inspectable callbacks.
- TokenTracker instance.

**Input:**
- Invoke the provider's `invoke()` method with the tracker registered.

**Expected:**
- The tracker appears in the callbacks list passed to the LLM.
- After invocation, the tracker has recorded token usage from the call.

**Assertion pseudocode:**
```
tracker = TokenTracker()
provider = MockProvider()
provider.invoke(prompt, callbacks=[tracker])
ASSERT tracker in provider.last_callbacks
ASSERT tracker.total_tokens > 0
```

---

### TS-15-17: Post-mortem is a terminal graph node

**Requirement:** 15-REQ-3.3
**Type:** unit
**Description:** Verify `generate_postmortem` is a dedicated terminal node
in the LangGraph that reads final state and returns it unchanged.

**Preconditions:**
- Halted graph state with halt_reason set.

**Input:**
- Call `generate_postmortem_node(state)`.

**Expected:**
- Post-mortem file is written.
- The returned state is identical to the input state (unchanged).

**Assertion pseudocode:**
```
state = halted_state_with_reason("max attempts exceeded")
returned_state = generate_postmortem_node(state)
ASSERT (worktree / "_postmortem.md").exists()
ASSERT returned_state == state
```

---

### TS-15-18: Console shows token usage and elapsed time after LLM call

**Requirement:** 15-REQ-4.3
**Type:** unit
**Description:** Verify console output includes running token usage and
elapsed time after each LLM call.

**Preconditions:**
- ConsoleLogger with captured output.

**Input:**
- `logger.log_token_usage(input_tokens=500, output_tokens=200, elapsed=45.3)`.

**Expected:**
- Output contains token counts and elapsed time.

**Assertion pseudocode:**
```
with capture_output() as out:
    logger.log_token_usage(input_tokens=500, output_tokens=200, elapsed=45.3)
ASSERT "500" in out or "700" in out
ASSERT "45" in out
```

---

### TS-15-19: Console uses rich with color coding

**Requirement:** 15-REQ-4.4
**Type:** unit
**Description:** Verify console output uses `rich.console.Console` and
applies color coding: green for pass, red for fail, yellow for warnings,
blue for phase transitions.

**Preconditions:**
- ConsoleLogger with `force_terminal=True` to enable color output.

**Input:**
- `logger.log_test_result(VerificationResult(passed=True, ...))` (green).
- `logger.log_test_result(VerificationResult(passed=False, ...))` (red).
- `logger.log_transition("implement", ...)` (blue).

**Expected:**
- Output contains ANSI color codes corresponding to the expected colors.

**Assertion pseudocode:**
```
logger = ConsoleLogger(force_terminal=True)
with capture_output() as out:
    logger.log_test_result(VerificationResult(passed=True, exit_code=0, stdout="3 passed"))
ASSERT "\033[" in out  -- contains ANSI escape
```

---

### TS-15-20: Circuit breaker completes in-flight LLM call before halt

**Requirement:** 15-REQ-5.1
**Type:** unit
**Description:** Verify that when a circuit breaker trips, the system
completes the current LLM call (does not abort mid-stream) before
transitioning to the post-mortem node.

**Preconditions:**
- CircuitBreaker with `max_attempts_per_task=1`.
- Mock LLM call in progress.

**Input:**
- Trigger circuit breaker check during an LLM call sequence.

**Expected:**
- The LLM call completes and its response is received.
- Halt occurs after the call completes, not during.

**Assertion pseudocode:**
```
cb = CircuitBreaker(SafetyConfig(max_attempts_per_task=1))
call_completed = False

def mock_llm_call():
    nonlocal call_completed
    response = llm.invoke(prompt)  -- completes fully
    call_completed = True
    return response

result = run_with_circuit_breaker(cb, mock_llm_call)
ASSERT call_completed == True
ASSERT result.halted == True
```

---

### TS-15-21: Worktree left intact on shutdown

**Requirement:** 15-REQ-5.3
**Type:** unit
**Description:** Verify the worktree is not merged or deleted during
graceful shutdown.

**Preconditions:**
- Worktree directory with partial work (uncommitted files).

**Input:**
- Trigger graceful shutdown.

**Expected:**
- Worktree directory still exists after shutdown.
- Files in worktree are untouched.

**Assertion pseudocode:**
```
worktree = create_test_worktree_with_files()
marker_file = worktree / "partial_work.py"
marker_file.write_text("partial")

perform_graceful_shutdown(state, worktree, tracker)

ASSERT worktree.exists()
ASSERT marker_file.exists()
ASSERT marker_file.read_text() == "partial"
```

---

### TS-15-22: Run summary file written to worktree

**Requirement:** 15-REQ-6.1
**Type:** unit
**Description:** Verify `_run_summary.md` is written to the worktree
directory and its path is logged.

**Preconditions:**
- Completed execution state.
- Writable worktree directory.

**Input:**
- `write_run_summary(state, worktree, tracker)`.

**Expected:**
- `_run_summary.md` exists in the worktree directory.
- Path is logged to console.

**Assertion pseudocode:**
```
with capture_logs() as logs:
    path = write_run_summary(state, tmp_worktree, tracker)
ASSERT path == tmp_worktree / "_run_summary.md"
ASSERT path.exists()
ASSERT any("_run_summary.md" in log for log in logs)
```

---

### TS-15-23: Condensed summary printed to console

**Requirement:** 15-REQ-6.3
**Type:** unit
**Description:** Verify a condensed run summary is printed to the console
at the end of execution.

**Preconditions:**
- ConsoleLogger with captured output.
- Completed execution state with known values.

**Input:**
- `logger.print_summary(state, tracker)`.

**Expected:**
- Console output contains spec name, status, token count, and elapsed time.

**Assertion pseudocode:**
```
with capture_output() as out:
    logger.print_summary(state, tracker)
ASSERT "success" in out.lower() or "failed" in out.lower()
ASSERT "token" in out.lower()
```

---

### TS-15-24: Safety config passed to circuit breaker and graph state

**Requirement:** 15-REQ-7.3
**Type:** unit
**Description:** Verify the safety configuration is passed to the circuit
breaker at initialization and to the graph state as `max_attempts`.

**Preconditions:**
- CoderConfig with custom safety limits.

**Input:**
- Create CircuitBreaker from config.
- Initialize graph state from config.

**Expected:**
- CircuitBreaker uses the configured limits.
- Graph state contains `max_attempts` matching the config value.

**Assertion pseudocode:**
```
config = CoderConfig(safety=SafetyConfig(max_attempts_per_task=7))
cb = CircuitBreaker(config.safety)
ASSERT cb.config.max_attempts_per_task == 7

state = create_initial_state(config)
ASSERT state["max_attempts"] == 7
```

---

### TS-15-E7: Summary write failure falls back to console

**Requirement:** 15-REQ-6.E1
**Type:** unit
**Description:** Verify console fallback when file write fails.

**Preconditions:**
- Read-only worktree directory.

**Input:**
- `write_run_summary(state, read_only_dir, tracker)`.

**Expected:**
- No exception raised. Warning logged. Summary printed to console.

**Assertion pseudocode:**
```
with capture_output() as out, capture_logs() as logs:
    write_run_summary(state, read_only_dir, tracker)
ASSERT any("warning" in log for log in logs)
ASSERT len(out) > 0  -- printed to console instead
```

## Integration Smoke Tests

### TS-15-SMOKE-1: Circuit breaker halts graph execution

**Execution Path:** Path 1 from design.md
**Description:** Verify circuit breaker integration with LangGraph — graph
halts and produces post-mortem when limit is breached.

**Setup:** Mock LLM that always fails tests. SafetyConfig with
`max_attempts_per_task=2`. Real LangGraph execution.

**Trigger:** `run_spec(spec, mock_provider, worktree, config)`

**Expected side effects:**
- RunResult with `success=False` and `halt_reason` mentioning attempts.
- `_postmortem.md` exists in worktree.
- `_run.json` shows `halted=True`.
- Implement node called at most 2 times.

**Must NOT satisfy with:** Mocking CircuitBreaker — real limit checking
must execute within the graph.

**Assertion pseudocode:**
```
config = CoderConfig(safety=SafetyConfig(max_attempts_per_task=2))
result = run_spec(spec, always_fail_provider, wt, config)
ASSERT result.success == False
ASSERT "attempt" in result.halt_reason
ASSERT (wt / "_postmortem.md").exists()
```

---

### TS-15-SMOKE-2: Token tracking end-to-end

**Execution Path:** Path 2 from design.md
**Description:** Verify tokens are tracked across multiple LLM calls
during graph execution.

**Setup:** Mock LLM that reports token counts. Real TokenTracker callback.

**Trigger:** `run_spec(spec, mock_provider, worktree, config)`

**Expected side effects:**
- RunResult has `total_tokens > 0`.
- Token count reflects accumulated usage from all calls.

**Must NOT satisfy with:** Mocking TokenTracker — real callback handler
must receive events from the LLM calls.

**Assertion pseudocode:**
```
result = run_spec(spec, mock_provider_with_tokens, wt, config)
ASSERT result.total_tokens > 0
```

## Coverage Matrix

| Requirement | Test Spec Entry | Type |
|-------------|-----------------|------|
| 15-REQ-1.1 | TS-15-1 | unit |
| 15-REQ-1.2 | TS-15-2 | unit |
| 15-REQ-1.3 | TS-15-3 | unit |
| 15-REQ-1.4 | TS-15-4 | unit |
| 15-REQ-1.5 | TS-15-15 | unit |
| 15-REQ-1.E1 | TS-15-E1 | unit |
| 15-REQ-1.E2 | TS-15-E2 | unit |
| 15-REQ-2.1 | TS-15-5 | unit |
| 15-REQ-2.2 | TS-15-6 | unit |
| 15-REQ-2.3 | TS-15-7, TS-15-8 | unit |
| 15-REQ-2.E1 | TS-15-E3 | unit |
| 15-REQ-3.1 | TS-15-10 | unit |
| 15-REQ-3.2 | TS-15-9 | unit |
| 15-REQ-3.4 | TS-15-E4 | unit |
| 15-REQ-3.E1 | TS-15-E4 | unit |
| 15-REQ-4.1 | TS-15-11 | unit |
| 15-REQ-4.2 | TS-15-12 | unit |
| 15-REQ-4.5 | TS-15-11 | unit |
| 15-REQ-4.E1 | TS-15-E5 | unit |
| 15-REQ-5.2 | TS-15-13 | unit |
| 15-REQ-5.E1 | TS-15-E6 | integration |
| 15-REQ-6.2 | TS-15-14 | unit |
| 15-REQ-6.E1 | TS-15-E7 | unit |
| 15-REQ-7.1 | TS-15-15 | unit |
| 15-REQ-7.2 | TS-15-15 | unit |
| 15-REQ-2.4 | TS-15-16 | unit |
| 15-REQ-3.3 | TS-15-17 | unit |
| 15-REQ-4.3 | TS-15-18 | unit |
| 15-REQ-4.4 | TS-15-19 | unit |
| 15-REQ-5.1 | TS-15-20 | unit |
| 15-REQ-5.3 | TS-15-21 | unit |
| 15-REQ-6.1 | TS-15-22 | unit |
| 15-REQ-6.3 | TS-15-23 | unit |
| 15-REQ-7.3 | TS-15-24 | unit |
| Property 1 | TS-15-P1 | property |
| Property 2 | TS-15-P2 | property |
| Property 3 | TS-15-P3 | property |
| Property 4 | TS-15-P4 | property |
| Path 1 | TS-15-SMOKE-1 | integration |
| Path 2 | TS-15-SMOKE-2 | integration |
