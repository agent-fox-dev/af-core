"""Entry points for spec and campaign execution.

Provides ``run_spec()`` and ``run_campaign()`` functions that build and
execute the LangGraph workflow for one or more specs.

Implements Requirements:
    14-REQ-9.1 (run_spec), 14-REQ-9.2 (RunResult),
    14-REQ-9.3 (run_campaign), 14-REQ-9.E1 (exception handling),
    14-REQ-7.1 (task group iteration), 14-REQ-7.2 (commit format),
    14-REQ-7.3 (task group advance), 14-REQ-7.4 (complete phase),
    14-REQ-5.1 (worktree creation), 14-REQ-5.3 (worktree merge),
    14-REQ-5.4 (worktree cleanup).

    15-REQ-1.4 (circuit breaker integration via config),
    15-REQ-2.4 (token tracker registration via TrackedProvider),
    15-REQ-4.1 (console logging integration),
    15-REQ-5.E1 (SIGINT handler installation),
    15-REQ-6.1 (run summary generation),
    15-REQ-7.3 (safety config passed to graph state).
"""

from __future__ import annotations

import logging
import signal
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from coder.graph import build_graph, create_initial_state
from coder.models import ExecutionPlan, ParsedSpec
from coder.state import persist_state
from coder.tools import create_coding_tools
from coder.worktree import (
    cleanup_worktree,
    commit_task_group,
    create_worktree,
    merge_worktree,
)

logger = logging.getLogger(__name__)


@dataclass
class RunResult:
    """Result of executing a single spec through the TDD workflow.

    Attributes:
        success: Whether the spec completed successfully.
        spec_name: Name of the spec that was executed.
        task_groups_completed: Number of task groups completed.
        total_task_groups: Total number of task groups in the spec.
        total_tokens: Total tokens consumed during execution.
        elapsed_seconds: Wall-clock time in seconds.
        halt_reason: Reason for halting, or None if successful.
    """

    success: bool
    spec_name: str
    task_groups_completed: int
    total_task_groups: int
    total_tokens: int
    elapsed_seconds: float
    halt_reason: str | None = None


# ---------------------------------------------------------------------------
# Provider wrapper for token tracking (15-REQ-2.4)
# ---------------------------------------------------------------------------


class _LLMResponseProxy:
    """Minimal response container for TokenTracker.on_llm_end().

    The tracker expects ``response.llm_output`` to be a dict containing
    a ``token_usage`` sub-dict.
    """

    __slots__ = ("llm_output",)

    def __init__(self, llm_output: dict[str, Any]) -> None:
        self.llm_output = llm_output


class _TrackedProvider:
    """Wraps an LLM provider to feed token usage to a TokenTracker.

    After each ``invoke()`` call, extracts token usage metadata from the
    response and calls ``tracker.on_llm_end()`` so that the tracker
    accumulates totals (15-REQ-2.4).
    """

    def __init__(self, provider: Any, tracker: Any) -> None:
        self._provider = provider
        self._tracker = tracker

    @property
    def model_name(self) -> str:
        return getattr(self._provider, "model_name", "unknown")

    def invoke(
        self,
        messages: Any,
        tools: Any = None,
    ) -> Any:
        """Invoke the underlying provider and track token usage."""
        result = self._provider.invoke(messages, tools)

        # Extract token metadata and feed to tracker
        llm_output = getattr(result, "llm_output", None)
        if llm_output and isinstance(llm_output, dict):
            self._tracker.on_llm_end(
                _LLMResponseProxy(llm_output)
            )
        elif hasattr(result, "response_metadata"):
            metadata = result.response_metadata
            if isinstance(metadata, dict):
                # LangChain chat models put usage in response_metadata
                usage = metadata.get("usage") or metadata.get(
                    "token_usage"
                )
                if usage and isinstance(usage, dict):
                    self._tracker.on_llm_end(
                        _LLMResponseProxy({"token_usage": usage})
                    )

        return result

    def validate(self) -> None:
        """Delegate to underlying provider if available."""
        if hasattr(self._provider, "validate"):
            self._provider.validate()


# ---------------------------------------------------------------------------
# Safety component factory
# ---------------------------------------------------------------------------


def _create_safety_components(
    config: dict[str, Any],
    start_time: float,
) -> dict[str, Any]:
    """Create safety & observability components from config.

    Reads the ``safety`` key from the config dict and creates a
    CircuitBreaker, TokenTracker, and ConsoleLogger.

    Parameters
    ----------
    config:
        Configuration dictionary with optional ``safety`` key containing
        ``max_attempts_per_task``, ``max_wall_time_seconds``,
        ``max_tokens``.
    start_time:
        Execution start time (epoch seconds) for the circuit breaker.

    Returns
    -------
    A dict with keys: ``circuit_breaker``, ``token_tracker``,
    ``console_logger``, ``safety_config``. Values are ``None`` when
    safety is not configured.
    """
    from coder.circuit import CircuitBreaker
    from coder.config import SafetyConfig
    from coder.console import ConsoleLogger
    from coder.tokens import TokenTracker

    safety_dict = config.get("safety")
    if safety_dict is None:
        return {
            "circuit_breaker": None,
            "token_tracker": TokenTracker(),
            "console_logger": ConsoleLogger(),
            "safety_config": SafetyConfig(),
        }

    # Build SafetyConfig from the config dict
    if isinstance(safety_dict, dict):
        safety_config = SafetyConfig(**safety_dict)
    else:
        # Already a SafetyConfig object
        safety_config = safety_dict

    tracker = TokenTracker()
    console = ConsoleLogger()
    breaker = CircuitBreaker(safety_config, start_time=start_time)

    return {
        "circuit_breaker": breaker,
        "token_tracker": tracker,
        "console_logger": console,
        "safety_config": safety_config,
    }


# ---------------------------------------------------------------------------
# Spec execution
# ---------------------------------------------------------------------------


def run_spec(
    parsed_spec: ParsedSpec,
    provider: Any,
    worktree_path: Path,
    config: dict[str, Any],
) -> RunResult:
    """Build and execute the LangGraph workflow for a single spec.

    Constructs the graph, initializes state, executes the workflow,
    and persists the final state to ``_run.json`` in the worktree.

    When a ``safety`` key is present in *config*, creates a
    CircuitBreaker, TokenTracker, and ConsoleLogger, wires them into
    the graph, and generates post-mortem and run summary documents
    after execution completes.

    Parameters
    ----------
    parsed_spec:
        The parsed spec pack to execute.
    provider:
        The LLM provider to use for all nodes.
    worktree_path:
        Path to the worktree directory for isolated execution.
    config:
        Configuration dictionary for the execution.

    Returns
    -------
    A :class:`RunResult` with success/fail status and statistics.
    """
    start_time = time.monotonic()
    wall_start = time.time()
    total_groups = len(parsed_spec.tasks.task_groups)
    if total_groups == 0:
        total_groups = 1

    # -- Create safety & observability components ----------------------------
    safety = _create_safety_components(config, wall_start)
    safety_config = safety["safety_config"]
    circuit_breaker = safety["circuit_breaker"]
    token_tracker = safety["token_tracker"]
    console_logger = safety["console_logger"]

    # Wrap the provider with token tracking (15-REQ-2.4)
    if token_tracker is not None:
        tracked_provider = _TrackedProvider(provider, token_tracker)
    else:
        tracked_provider = provider

    # Build tools bound to the worktree
    tools = create_coding_tools(worktree_path)
    tool_list = list(tools.values())

    # Build the LangGraph workflow -- pass safety components via config
    graph_config: dict[str, Any] = dict(config)
    graph_config["circuit_breaker"] = circuit_breaker
    graph_config["token_tracker"] = token_tracker
    graph_config["console_logger"] = console_logger
    graph_config["start_time"] = wall_start

    graph = build_graph(tracked_provider, tool_list, graph_config)

    # Initialize state from the parsed spec (15-REQ-7.3)
    state = create_initial_state(parsed_spec, safety_config=safety_config)

    # Add safety-related fields to state for the postmortem node
    model_name = getattr(provider, "model_name", "unknown")
    state["worktree"] = str(worktree_path)
    state["token_tracker"] = token_tracker
    state["spec_name"] = parsed_spec.meta.spec_name
    state["model_name"] = model_name

    # Install SIGINT handler for graceful shutdown (15-REQ-5.E1)
    previous_handler = None
    try:
        from coder.postmortem import install_sigint_handler

        previous_handler = install_sigint_handler(
            state, worktree_path, token_tracker
        )
    except Exception as exc:
        logger.warning("Failed to install SIGINT handler: %s", exc)

    # Execute the graph
    try:
        final_state = graph.invoke(state)
    except Exception as exc:
        elapsed = time.monotonic() - start_time
        logger.error(
            "Graph execution failed for spec %s: %s",
            parsed_spec.meta.spec_name,
            exc,
        )
        # Generate run summary even on failure
        total_tokens = (
            token_tracker.total_tokens
            if token_tracker is not None
            else 0
        )
        return RunResult(
            success=False,
            spec_name=parsed_spec.meta.spec_name,
            task_groups_completed=0,
            total_task_groups=total_groups,
            total_tokens=total_tokens,
            elapsed_seconds=max(elapsed, 0.001),
            halt_reason=f"Graph execution error: {exc}",
        )
    finally:
        # Restore previous SIGINT handler
        if previous_handler is not None:
            try:
                signal.signal(signal.SIGINT, previous_handler)
            except (OSError, ValueError):
                pass

    # Persist final state to _run.json
    persist_state(final_state, worktree_path)

    elapsed = time.monotonic() - start_time

    # Determine success from final state
    halted = final_state.get("halted", False)
    halt_reason = final_state.get("halt_reason", "") or None
    current_phase = final_state.get("current_phase", "")
    success = current_phase == "complete" and not halted
    task_groups_completed = final_state.get("current_task_group", 1)
    if success:
        task_groups_completed = total_groups

    total_tokens = (
        token_tracker.total_tokens if token_tracker is not None else 0
    )

    # -- Post-execution: run summary and console output ----------------------

    # Enrich state for summary/postmortem generation
    final_state["elapsed_seconds"] = elapsed
    final_state["success"] = success

    # Write run summary (15-REQ-6.1)
    try:
        from coder.summary import write_run_summary

        write_run_summary(final_state, worktree_path, token_tracker)
    except Exception as exc:
        logger.warning("Failed to write run summary: %s", exc)

    # Print condensed summary to console (15-REQ-6.3)
    if console_logger is not None:
        status = "success" if success else ("halted" if halted else "failed")
        summary_text = (
            f"Spec: {parsed_spec.meta.spec_name} | "
            f"Status: {status} | "
            f"Tokens: {total_tokens:,} | "
            f"Elapsed: {elapsed:.1f}s"
        )
        console_logger.print_summary(summary_text)

    return RunResult(
        success=success,
        spec_name=parsed_spec.meta.spec_name,
        task_groups_completed=task_groups_completed,
        total_task_groups=total_groups,
        total_tokens=total_tokens,
        elapsed_seconds=max(elapsed, 0.001),
        halt_reason=halt_reason if not success else None,
    )


def run_campaign(
    plan: ExecutionPlan,
    provider: Any,
    repo_path: Path,
    config: dict[str, Any],
) -> list[RunResult]:
    """Iterate over specs in plan order, running each and collecting results.

    For each spec: creates a worktree (14-REQ-5.1), runs ``run_spec``
    within the worktree (14-REQ-5.2), commits on success (14-REQ-7.2),
    merges the worktree branch back (14-REQ-5.3), and cleans up
    (14-REQ-5.4). Catches per-spec exceptions so that a failure in one
    spec does not prevent execution of subsequent specs (14-REQ-9.E1).

    Parameters
    ----------
    plan:
        The execution plan with ordered specs.
    provider:
        The LLM provider to use for all specs.
    repo_path:
        Path to the repository root.
    config:
        Configuration dictionary for the execution.

    Returns
    -------
    A list of :class:`RunResult` objects, one per spec.
    """
    results: list[RunResult] = []
    model_name = getattr(provider, "model_name", "unknown")

    for spec in plan.specs:
        start_time = time.monotonic()
        total_groups = len(spec.tasks.task_groups) or 1
        wt = None

        try:
            # Create isolated worktree for this spec (14-REQ-5.1)
            wt = create_worktree(
                repo_path,
                spec.meta.spec_name,
                model_name,
            )

            # Execute spec in the worktree (14-REQ-5.2)
            result = run_spec(spec, provider, wt.path, config)
            results.append(result)

            if result.success:
                # Commit task group completion (14-REQ-7.2)
                commit_task_group(
                    wt,
                    result.task_groups_completed,
                    spec.meta.spec_name,
                )
                # Merge worktree branch back to source (14-REQ-5.3)
                merge_worktree(wt)
        except Exception as exc:
            elapsed = time.monotonic() - start_time
            logger.error(
                "Spec %s failed with error: %s",
                spec.meta.spec_name,
                exc,
            )
            results.append(
                RunResult(
                    success=False,
                    spec_name=spec.meta.spec_name,
                    task_groups_completed=0,
                    total_task_groups=total_groups,
                    total_tokens=0,
                    elapsed_seconds=elapsed,
                    halt_reason=f"Error: {exc}",
                )
            )
        finally:
            # Clean up worktree regardless of outcome (14-REQ-5.4)
            if wt is not None:
                try:
                    cleanup_worktree(wt)
                except Exception as cleanup_exc:
                    logger.warning(
                        "Failed to clean up worktree for %s: %s",
                        spec.meta.spec_name,
                        cleanup_exc,
                    )

    return results
