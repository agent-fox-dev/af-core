"""LangGraph state schema and conditional edge routing.

Defines the ``CoderState`` TypedDict used as the shared state across all
graph nodes, the factory function to create initial state, the routing
functions that encode retry / loop-back logic for the TDD workflow, and
the ``build_graph`` constructor that assembles the compiled LangGraph.

Implements Requirements:
    14-REQ-1.1 (state schema), 14-REQ-1.2 (initial defaults),
    14-REQ-3.1 (coverage routing), 14-REQ-3.2 (test failure routing),
    14-REQ-3.3 (test pass routing), 14-REQ-3.4 (drift routing),
    14-REQ-3.5 (no-drift routing), 14-REQ-3.6 (halt routing),
    14-REQ-9.1 (graph construction, partial).

    15-REQ-1.4 (halt on breach via node wrapper),
    15-REQ-2.4 (token tracker callback via TrackedProvider),
    15-REQ-3.3 (generate_postmortem terminal node),
    15-REQ-4.1 (console phase transitions via node wrapper),
    15-REQ-4.2 (console test results via node wrapper),
    15-REQ-4.3 (console token usage via node wrapper).
"""

from __future__ import annotations

import logging
import time
from typing import Any, TypedDict

from langgraph.graph import END, StateGraph

from coder.models import ParsedSpec

logger = logging.getLogger(__name__)

# -- Node categories for wrapper logic ----------------------------------------

_LLM_NODES = frozenset({
    "understand_spec",
    "analyze_codebase",
    "write_tests",
    "verify_test_coverage",
    "implement",
    "verify_intent",
})
"""Nodes that invoke the LLM -- token usage is logged after these."""

_TERMINAL_NODES = frozenset({
    "complete",
    "halted",
    "generate_postmortem",
})
"""Terminal nodes -- circuit breaker is not checked after these."""


class _NullTracker:
    """Null token tracker used when no real tracker is provided."""

    @property
    def total_tokens(self) -> int:
        return 0


_null_tracker = _NullTracker()


class CoderState(TypedDict, total=False):
    """Shared state for the LangGraph TDD workflow.

    All fields use ``total=False`` so that nodes can read missing keys
    via ``.get()`` and fall back to sensible defaults per 14-REQ-1.E1.
    """

    current_phase: str
    current_task_group: int
    attempt_count: int
    max_attempts: int
    test_results: str
    spec_context: str
    codebase_analysis: str
    coverage_ok: bool
    drift_detected: bool
    messages: list[Any]
    halted: bool
    halt_reason: str
    history: list[Any]
    total_groups: int
    # Safety & observability fields (spec 15)
    worktree: str
    token_tracker: Any
    spec_name: str
    model_name: str
    success: bool
    elapsed_seconds: float


def create_initial_state(
    parsed_spec: ParsedSpec,
    safety_config: Any = None,
) -> dict[str, Any]:
    """Create the initial CoderState for a spec execution.

    Parameters
    ----------
    parsed_spec:
        The parsed spec pack to execute.
    safety_config:
        Optional safety configuration object with a
        ``max_attempts_per_task`` attribute. If provided, its value
        overrides the default ``max_attempts`` (5).

    Returns
    -------
    A dictionary conforming to :class:`CoderState` with default values
    per 14-REQ-1.2, 15-REQ-7.3.
    """
    total_groups = len(parsed_spec.tasks.task_groups)

    # Determine max_attempts: safety config overrides the default (15-REQ-7.3)
    max_attempts = 5
    if safety_config is not None:
        cfg_max = getattr(safety_config, "max_attempts_per_task", None)
        if cfg_max is not None:
            max_attempts = cfg_max

    return {
        "current_phase": "understand_spec",
        "current_task_group": 1,
        "attempt_count": 0,
        "max_attempts": max_attempts,
        "test_results": "",
        "spec_context": "",
        "codebase_analysis": "",
        "coverage_ok": False,
        "drift_detected": False,
        "messages": [],
        "halted": False,
        "halt_reason": "",
        "history": [],
        "total_groups": total_groups if total_groups > 0 else 1,
    }


# ---------------------------------------------------------------------------
# Conditional edge routing functions
# ---------------------------------------------------------------------------


def route_after_coverage(state: dict[str, Any]) -> str:
    """Route after the ``verify_test_coverage`` node.

    14-REQ-3.1: coverage insufficient -> write_tests
    Otherwise -> implement

    Parameters
    ----------
    state:
        Current graph state.

    Returns
    -------
    Name of the next node.
    """
    if not state.get("coverage_ok", False):
        return "write_tests"
    return "implement"


def route_after_tests(state: dict[str, Any]) -> str:
    """Route after the ``run_tests`` node.

    14-REQ-3.3: tests pass -> verify_intent
    14-REQ-3.6: tests fail + max attempts -> halted
    14-REQ-3.2: tests fail + attempts left -> implement

    Parameters
    ----------
    state:
        Current graph state.

    Returns
    -------
    Name of the next node.
    """
    # If already halted (e.g. by circuit breaker), route to halted
    if state.get("halted", False):
        return "halted"

    test_results = state.get("test_results", "")
    attempt_count = state.get("attempt_count", 0)
    max_attempts = state.get("max_attempts", 5)

    if test_results.upper() == "PASS":
        return "verify_intent"

    # Test failure path
    if attempt_count >= max_attempts:
        return "halted"

    return "implement"


def route_after_intent(state: dict[str, Any]) -> str:
    """Route after the ``verify_intent`` node.

    14-REQ-3.5: no drift + last group -> complete
    14-REQ-3.5: no drift + more groups -> next_task_group
    14-REQ-3.6: drift + max attempts -> halted
    14-REQ-3.4: drift + attempts left -> verify_test_coverage

    Parameters
    ----------
    state:
        Current graph state.

    Returns
    -------
    Name of the next node.
    """
    # If already halted (e.g. by circuit breaker), route to halted
    if state.get("halted", False):
        return "halted"

    drift_detected = state.get("drift_detected", False)
    attempt_count = state.get("attempt_count", 0)
    max_attempts = state.get("max_attempts", 5)
    current_group = state.get("current_task_group", 1)
    total_groups = state.get("total_groups", 1)

    if not drift_detected:
        if current_group >= total_groups:
            return "complete"
        return "next_task_group"

    # Drift detected
    if attempt_count >= max_attempts:
        return "halted"

    return "verify_test_coverage"


# ---------------------------------------------------------------------------
# Graph construction
# ---------------------------------------------------------------------------


def build_graph(
    provider: Any,
    tools: list[Any],
    config: dict[str, Any],
) -> Any:
    """Construct the LangGraph state machine with all nodes and edges.

    Creates the full TDD workflow graph with node wrappers that bind the
    LLM provider and verification runner to each node function, then
    compiles it into an executable graph.

    The node wrapper pattern (15-REQ-1.4) checks the circuit breaker
    after each non-terminal node, logs phase transitions and token usage
    via the console logger, and increments the attempt counter when
    entering the ``implement`` node.

    Parameters
    ----------
    provider:
        An :class:`LLMProvider` instance (or mock) used by LLM-calling
        nodes. Must have an ``invoke(messages)`` method.
    tools:
        List of LangChain tool definitions available to the LLM.
    config:
        Configuration dictionary. Recognised keys:

        - ``verification_runner``: a :class:`VerificationRunner` instance
          (or mock) used by the ``run_tests`` node. If absent, the
          ``run_tests`` node will be a no-op that marks tests as passed.
        - ``circuit_breaker``: a :class:`CircuitBreaker` instance for
          enforcing safety limits at each node transition (15-REQ-1.4).
        - ``token_tracker``: a :class:`TokenTracker` instance for
          accumulating token counts (15-REQ-2.4).
        - ``console_logger``: a :class:`ConsoleLogger` instance for
          formatted console output (15-REQ-4.1).
        - ``start_time``: a ``float`` (epoch seconds) marking execution
          start for elapsed-time display. Defaults to ``time.time()``.

    Returns
    -------
    A compiled LangGraph ``CompiledGraph`` ready for ``.invoke(state)``.
    """
    from coder.nodes import (
        _with_defaults,
        analyze_codebase,
        complete_node,
        halted_node,
        implement,
        next_task_group,
        run_tests,
        understand_spec,
        verify_intent,
        verify_test_coverage,
        write_tests,
    )
    from coder.postmortem import generate_postmortem_node

    runner = config.get("verification_runner")
    circuit_breaker = config.get("circuit_breaker")
    token_tracker = config.get("token_tracker")
    console_logger = config.get("console_logger")
    start_time = config.get("start_time", time.time())

    # -- Node wrapper (15-REQ-1.4, 15-REQ-4.1, 15-REQ-4.2, 15-REQ-4.3) ------

    def _wrap_node(
        node_fn: Any,
        node_name: str,
    ) -> Any:
        """Wrap a node function with safety and observability hooks.

        1. Log phase transition via ConsoleLogger.
        2. Increment ``attempt_count`` when entering ``implement`` (if CB
           is active) -- each implement entry counts as one attempt.
        3. Execute the original node function.
        4. Log token usage after LLM-calling nodes.
        5. Check the circuit breaker; if halted, set halt flags.
        """

        def _wrapped(state: CoderState) -> CoderState:
            state_dict: dict[str, Any] = dict(state)

            # 1. Log phase transition
            if console_logger is not None:
                console_logger.log_transition(
                    node_name,
                    task_group=state_dict.get("current_task_group", 1),
                    attempt=state_dict.get("attempt_count", 0),
                    max_attempts=state_dict.get("max_attempts", 5),
                )

            # 2. Increment attempt count for implement node.
            #    This counts each visit to the implement node as one
            #    "implementation attempt" for the circuit breaker.
            #    Only active when a circuit breaker is configured to
            #    preserve backward compatibility with spec 14 behavior.
            if node_name == "implement" and circuit_breaker is not None:
                state_dict["attempt_count"] = (
                    state_dict.get("attempt_count", 0) + 1
                )

            # 3. Execute the node
            result_state: dict[str, Any] = node_fn(state_dict)
            if not isinstance(result_state, dict):
                result_state = dict(result_state)

            # 4. Log token usage after LLM-calling nodes
            if (
                console_logger is not None
                and token_tracker is not None
                and node_name in _LLM_NODES
            ):
                elapsed = time.time() - start_time
                console_logger.log_token_usage(token_tracker, elapsed)

            # 5. Check circuit breaker (15-REQ-1.4, 15-REQ-5.1)
            #    Skip for terminal nodes -- they are already at the end.
            #    The CB check happens AFTER the LLM call completes, so
            #    in-flight calls are never aborted (15-REQ-5.1).
            if (
                circuit_breaker is not None
                and node_name not in _TERMINAL_NODES
            ):
                effective_tracker = (
                    token_tracker
                    if token_tracker is not None
                    else _null_tracker
                )
                check_result = circuit_breaker.check(
                    result_state, effective_tracker
                )
                if check_result.halted:
                    result_state["halted"] = True
                    result_state["halt_reason"] = (
                        check_result.reason or ""
                    )

            return result_state  # type: ignore[return-value]

        return _wrapped

    # -- Build the state graph ------------------------------------------------
    graph = StateGraph(CoderState)

    # LLM-calling nodes -- wrapped with safety & observability hooks
    graph.add_node(
        "understand_spec",
        _wrap_node(
            lambda state: understand_spec(state, provider),
            "understand_spec",
        ),
    )
    graph.add_node(
        "analyze_codebase",
        _wrap_node(
            lambda state: analyze_codebase(state, provider),
            "analyze_codebase",
        ),
    )
    graph.add_node(
        "write_tests",
        _wrap_node(
            lambda state: write_tests(state, provider),
            "write_tests",
        ),
    )
    graph.add_node(
        "verify_test_coverage",
        _wrap_node(
            lambda state: verify_test_coverage(state, provider),
            "verify_test_coverage",
        ),
    )
    graph.add_node(
        "implement",
        _wrap_node(
            lambda state: implement(state, provider),
            "implement",
        ),
    )

    def _run_tests_node(state: dict[str, Any]) -> dict[str, Any]:
        """Run tests node: uses the runner if available, otherwise passes."""
        if runner:
            return run_tests(state, runner)
        # No runner configured: treat tests as passing so graph can proceed
        new_state = _with_defaults(state)
        new_state["test_results"] = "PASS"
        return new_state

    graph.add_node(
        "run_tests",
        _wrap_node(_run_tests_node, "run_tests"),
    )
    graph.add_node(
        "verify_intent",
        _wrap_node(
            lambda state: verify_intent(state, provider),
            "verify_intent",
        ),
    )
    graph.add_node(
        "next_task_group",
        _wrap_node(
            lambda state: next_task_group(state),
            "next_task_group",
        ),
    )

    # Terminal nodes -- not wrapped with circuit breaker
    graph.add_node(
        "complete",
        lambda state: complete_node(state),
    )
    graph.add_node(
        "halted",
        lambda state: halted_node(state),
    )
    # Post-mortem terminal node (15-REQ-3.3) -- generates _postmortem.md
    # from the final halted state before the graph exits.
    graph.add_node(
        "generate_postmortem",
        lambda state: generate_postmortem_node(state),
    )

    # -- Wire edges -----------------------------------------------------------

    # Linear: understand_spec -> analyze_codebase -> write_tests
    graph.set_entry_point("understand_spec")
    graph.add_edge("understand_spec", "analyze_codebase")
    graph.add_edge("analyze_codebase", "write_tests")

    # write_tests -> verify_test_coverage
    graph.add_edge("write_tests", "verify_test_coverage")

    # verify_test_coverage -> conditional (coverage_ok?)
    graph.add_conditional_edges(
        "verify_test_coverage",
        route_after_coverage,
        {"write_tests": "write_tests", "implement": "implement"},
    )

    # implement -> run_tests
    graph.add_edge("implement", "run_tests")

    # run_tests -> conditional (pass / fail+retry / fail+halt)
    graph.add_conditional_edges(
        "run_tests",
        route_after_tests,
        {
            "verify_intent": "verify_intent",
            "implement": "implement",
            "halted": "halted",
        },
    )

    # verify_intent -> conditional (no drift / drift+retry / drift+halt)
    graph.add_conditional_edges(
        "verify_intent",
        route_after_intent,
        {
            "next_task_group": "next_task_group",
            "complete": "complete",
            "verify_test_coverage": "verify_test_coverage",
            "halted": "halted",
        },
    )

    # next_task_group -> write_tests (loop back for next group)
    graph.add_edge("next_task_group", "write_tests")

    # Terminal edges
    graph.add_edge("complete", END)
    # halted -> generate_postmortem -> END (15-REQ-3.3)
    graph.add_edge("halted", "generate_postmortem")
    graph.add_edge("generate_postmortem", END)

    logger.debug("LangGraph TDD workflow compiled with %d nodes", 11)

    return graph.compile()
