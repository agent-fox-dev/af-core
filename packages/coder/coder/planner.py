"""Execution plan builder for spec-driven campaigns.

Orchestrates spec discovery, parsing, status validation, dependency
analysis, and topological sorting to produce an ``ExecutionPlan`` that
the TDD engine consumes for sequential implementation.

Entry point: ``build_execution_plan(campaign_dir, spec_filter=None)``.
"""

from __future__ import annotations

import logging
from collections import deque
from datetime import datetime, timezone
from pathlib import Path

from afspec.discovery import (  # type: ignore[import-untyped]
    DependencyGraph,
    build_dependency_graph,
    discover_specs,
)
from afspec.exceptions import SpecError  # type: ignore[import-untyped]
from afspec.models import SpecMeta, Status  # type: ignore[import-untyped]

from coder.errors import DependencyCycleError
from coder.models import ExecutionPlan, ParsedSpec
from coder.spec_parser import SpecParser

logger = logging.getLogger(__name__)


def build_execution_plan(
    campaign_dir: Path | str,
    spec_filter: list[str] | None = None,
) -> ExecutionPlan:
    """Build an execution plan from a campaign directory.

    Discovers spec packs, parses their artifacts, filters to active-only,
    resolves dependencies, and returns an ordered ``ExecutionPlan``.

    Parameters
    ----------
    campaign_dir:
        Path to the campaign directory containing spec pack folders.
    spec_filter:
        Optional list of spec names to include. When provided, only specs
        whose ``spec_name`` is in this list are included in the plan.

    Returns
    -------
    ExecutionPlan
        A frozen model with topologically-sorted specs ready for
        sequential implementation.

    Raises
    ------
    FileNotFoundError
        If *campaign_dir* does not exist.
    DependencyCycleError
        If the dependency graph contains a cycle.
    """
    campaign_path = Path(campaign_dir)

    # Step 0: Validate campaign directory exists.
    if not campaign_path.is_dir():
        raise FileNotFoundError(
            f"Campaign directory does not exist: {campaign_path}"
        )

    # Step 1: Discover specs.
    logger.debug("Discovering specs in %s", campaign_path)
    try:
        metas = discover_specs(campaign_path)
    except SpecError:
        # discover_specs raises SpecError if root doesn't exist, but we
        # already checked above. Treat any SpecError as empty discovery.
        metas = []
    logger.debug("Discovered %d spec(s)", len(metas))

    if not metas:
        return _empty_plan()

    # Step 2: Parse all discovered specs.
    parser = SpecParser()
    parsed_specs: list[ParsedSpec] = []
    for meta in metas:
        logger.debug("Parsing spec '%s' (id=%s)", meta.spec_name, meta.spec_id)
        parsed = parser.parse(meta)
        parsed_specs.append(parsed)
    logger.debug("Parsed %d spec(s)", len(parsed_specs))

    # Step 3: Filter to active specs only.
    active_specs = _filter_active(parsed_specs)

    if not active_specs:
        logger.error(
            "All specs in campaign have non-active status — "
            "returning empty execution plan"
        )
        return _empty_plan()

    # Step 4: Apply optional name filter.
    if spec_filter is not None:
        active_specs = [
            s for s in active_specs if s.meta.spec_name in spec_filter
        ]
        logger.debug(
            "After spec_filter, %d spec(s) remain", len(active_specs)
        )
        if not active_specs:
            return _empty_plan()

    # Step 5: Build dependency graph and topologically sort.
    sorted_specs = _sort_by_dependencies(active_specs, campaign_path)

    # Step 6: Build and return the execution plan.
    timestamp = datetime.now(timezone.utc).isoformat()
    plan = ExecutionPlan(
        specs=sorted_specs,
        count=len(sorted_specs),
        timestamp=timestamp,
    )
    logger.debug(
        "Execution plan built: %d spec(s), order: %s",
        plan.count,
        [s.meta.spec_name for s in plan.specs],
    )
    return plan


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------


def _empty_plan() -> ExecutionPlan:
    """Return an empty execution plan with the current timestamp."""
    return ExecutionPlan(
        specs=[],
        count=0,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _filter_active(parsed_specs: list[ParsedSpec]) -> list[ParsedSpec]:
    """Keep only specs with active status, logging warnings for skipped ones.

    Specs whose status cannot be determined (or is not a recognized value)
    are treated as ``draft`` and skipped with a warning per REQ-3.E1.
    """
    active: list[ParsedSpec] = []
    for spec in parsed_specs:
        status = spec.meta.status
        # Normalise: status may be a Status enum or a raw string.
        status_value = status.value if isinstance(status, Status) else str(status)

        if status_value == "active":
            active.append(spec)
        else:
            logger.warning(
                "Skipping spec '%s' — status is '%s' (only active specs are included)",
                spec.meta.spec_name,
                status_value,
            )
    return active


def _sort_by_dependencies(
    specs: list[ParsedSpec],
    campaign_path: Path,
) -> list[ParsedSpec]:
    """Topologically sort specs respecting dependency declarations.

    Uses ``afspec.discovery.build_dependency_graph`` for graph construction
    and its ``topological_sort`` for ordering.  When multiple valid
    orderings exist, Kahn's algorithm with sorted seed nodes preserves
    ascending numeric-prefix order among peers.

    External dependencies (referencing specs not in the campaign) are
    logged as warnings and treated as satisfied.
    """
    active_metas = [s.meta for s in specs]
    spec_by_id = {s.meta.spec_id: s for s in specs}

    try:
        graph: DependencyGraph = build_dependency_graph(active_metas, campaign_path)
    except SpecError as exc:
        error_msg = str(exc)
        # Check for cycle error from afspec.
        if "cycle" in error_msg.lower():
            raise DependencyCycleError(
                error_msg,
                cycle=_extract_cycle_specs(error_msg),
            ) from exc
        # Check for unknown dependency (external dep).
        if "unknown dependency" in error_msg.lower() or "unknown" in error_msg.lower():
            logger.warning(
                "External dependency not found in campaign — treating "
                "as satisfied: %s",
                error_msg,
            )
            # Rebuild graph without the problematic external deps by
            # filtering metas to only those present in the campaign.
            graph = _build_graph_ignoring_external(active_metas, campaign_path)
        else:
            raise DependencyCycleError(error_msg) from exc

    sorted_ids = _numeric_topological_sort(graph)

    # Map IDs back to ParsedSpec objects, preserving topological order.
    sorted_specs: list[ParsedSpec] = []
    for sid in sorted_ids:
        if sid in spec_by_id:
            sorted_specs.append(spec_by_id[sid])

    return sorted_specs


def _numeric_sort_key(spec_id: str) -> tuple[int, str]:
    """Sort key that orders spec IDs numerically, falling back to
    lexicographic order for non-numeric IDs."""
    try:
        return (int(spec_id), spec_id)
    except ValueError:
        return (999999, spec_id)


def _numeric_topological_sort(graph: DependencyGraph) -> list[str]:
    """Topological sort using Kahn's algorithm with numeric ordering.

    Identical to ``DependencyGraph.topological_sort`` but seeds and
    processes zero-in-degree nodes in ascending *numeric* order
    rather than lexicographic order, satisfying REQ-4.4.
    """
    edges = graph.edges()
    all_ids = {e.from_spec for e in edges} | {e.to_spec for e in edges}
    # Include all spec IDs known to the graph.
    # Access internal state since DependencyGraph doesn't expose
    # all_spec_ids publicly.
    if hasattr(graph, "_all_spec_ids"):
        all_ids = set(graph._all_spec_ids)

    in_degree: dict[str, int] = {sid: 0 for sid in all_ids}
    adjacency: dict[str, list[str]] = {sid: [] for sid in all_ids}

    for edge in edges:
        adjacency[edge.from_spec].append(edge.to_spec)
        in_degree[edge.to_spec] += 1

    # Seed with zero in-degree nodes, sorted numerically.
    queue: deque[str] = deque(
        sorted(
            (sid for sid, deg in in_degree.items() if deg == 0),
            key=_numeric_sort_key,
        )
    )
    result: list[str] = []

    while queue:
        node = queue.popleft()
        result.append(node)
        for neighbor in sorted(adjacency[node], key=_numeric_sort_key):
            in_degree[neighbor] -= 1
            if in_degree[neighbor] == 0:
                queue.append(neighbor)

    return result


def _build_graph_ignoring_external(
    metas: list[SpecMeta],
    campaign_path: Path,
) -> DependencyGraph:
    """Build a dependency graph, silently dropping external deps.

    Reads tasks.json for each meta, strips dependency declarations that
    reference spec IDs not in the current set of metas, then builds
    the graph from the remaining edges.
    """
    import json

    from afspec.models import DependencyEdge  # type: ignore[import-untyped]

    known_ids = {m.spec_id for m in metas}
    edges: list[DependencyEdge] = []

    for meta in metas:
        tasks_path = Path(meta.dir) / "tasks.json"
        if not tasks_path.is_file():
            continue

        try:
            tasks_data = json.loads(tasks_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            continue

        for dep in tasks_data.get("dependencies", []):
            dep_spec = dep.get("depends_on_spec", "")
            if dep_spec in known_ids:
                edges.append(
                    DependencyEdge(
                        from_spec=dep_spec,
                        to_spec=meta.spec_id,
                        from_group=dep.get("from_group", 0),
                        to_group=dep.get("to_group", 0),
                        relationship=dep.get("relationship", ""),
                    )
                )

    all_spec_ids = sorted(known_ids)
    return DependencyGraph(edges, all_spec_ids)


def _extract_cycle_specs(error_msg: str) -> list[str]:
    """Extract spec IDs from a cycle error message.

    Returns a best-effort list of spec identifiers mentioned in the
    cycle description.
    """
    # The afspec cycle message looks like: "Dependency cycle detected: A -> B"
    if " -> " in error_msg:
        parts = error_msg.split(":")
        if len(parts) >= 2:
            cycle_part = parts[-1].strip()
            return [s.strip() for s in cycle_part.split(" -> ")]
    return []
