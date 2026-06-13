# PRD: Safety & Observability

## Intent

Prevent runaway agent execution through circuit breakers, provide detailed
post-mortem documentation when execution fails, and deliver verbose structured
logging that gives the user real-time visibility into what the agent is doing.

## Goals

1. Implement a circuit breaker that halts execution when any safety limit is
   breached: maximum attempts per task, maximum wall-clock time, maximum
   tokens consumed.
2. Track token usage across all LLM providers (Anthropic, Google, Ollama)
   using LangChain callback handlers.
3. Generate a post-mortem markdown document when execution fails or is halted
   by the circuit breaker, explaining where and why the agent got stuck.
4. Provide verbose structured logging using `rich` console output that shows
   agent activity, step transitions, test results, and token usage in
   real time.
5. Implement graceful shutdown: when a circuit breaker trips, the agent
   finishes the current LLM call, saves run state, generates the post-mortem,
   and exits cleanly.
6. Generate a run summary document on completion (success or failure) with
   execution statistics.

## Non-Goals

- No distributed tracing or external observability backends (Datadog, etc.).
- No cost estimation or billing integration.
- No alerting or notification system.
- No automatic recovery or retry after circuit breaker trip — manual restart
  only.

## Background

The user describes this as the "Ralph-loop" problem: a coding agent that keeps
trying the same failing approach indefinitely, consuming tokens without making
progress. The circuit breaker is the primary defense against this.

Agent-fox implements a `CircuitBreaker` class that checks three limits before
each launch: cost ceiling, session limit, and retry limit per node. The coder
package needs a similar pattern adapted for LangGraph execution.

Token tracking across providers is non-trivial because each provider reports
usage differently:
- Anthropic: `input_tokens`, `output_tokens` in response metadata.
- Google: `prompt_token_count`, `candidates_token_count`.
- Ollama: `prompt_eval_count`, `eval_count`.

LangChain provides callback handlers that normalize this into a unified
`token_usage` interface.

## Design Decisions

1. **Three circuit breaker limits**:
   - `max_attempts_per_task`: Maximum retries for a single task group before
     giving up (default: 5).
   - `max_wall_time_seconds`: Maximum wall-clock time for an entire spec
     execution (default: 1800 = 30 minutes, configurable).
   - `max_tokens`: Maximum total tokens (input + output) across all LLM calls
     in a run (default: 2,000,000, configurable).
   Any breach triggers immediate halt.
2. **LangChain callbacks for token tracking**: Use `BaseCallbackHandler`
   subclass that accumulates token counts from each LLM call. Works across
   all LangChain chat model providers. The callback is registered on every
   LLM invocation.
3. **Post-mortem format**: Markdown document written to the worktree
   directory (or project root if worktree creation failed). Contains:
   task context, attempt history with timestamps, last error/test output,
   token usage breakdown, graph state at time of failure.
4. **Rich console logging**: Use `rich.console.Console` for structured output.
   Show: current step/node name, model being used, task group progress,
   test pass/fail counts, token usage, elapsed time. Update in real time.
5. **Graceful shutdown**: The circuit breaker sets a flag in the LangGraph
   state. The next node transition checks this flag and routes to a
   `generate_postmortem` terminal node instead of continuing execution.
6. **Run summary**: Written to `_run_summary.md` in the worktree directory.
   Contains: spec name, model used, task groups completed, total tokens,
   total time, pass/fail status, post-mortem path (if applicable).
7. **Configuration via spec 12 config system**: Circuit breaker limits are
   set in `.coder.yaml` under a `safety:` key, with environment variable
   overrides (`CODER_MAX_ATTEMPTS`, `CODER_MAX_TIME`, `CODER_MAX_TOKENS`).

## Dependencies

| Spec | From Group | To Group | Relationship |
|------|-----------|----------|--------------|
| 12_coder_foundation | 2 | 1 | Uses configuration system and logging infrastructure from group 2 |
| 14_tdd_execution_engine | 3 | 1 | Wraps LangGraph execution with circuit breaker checks; needs graph state schema and node structure from group 3 |

## Source

Source: Input provided by user via interactive prompt.
