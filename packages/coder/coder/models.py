"""Data models for the coder execution planning layer.

Provides frozen pydantic models for parsed spec packs and execution plans.
These models are consumed by the TDD engine after the planner builds them
from a campaign directory.
"""

from __future__ import annotations

from afspec.models import (  # type: ignore[import-untyped]
    Requirements,
    SpecMeta,
    Tasks,
    TestSpec,
)
from pydantic import BaseModel, ConfigDict


class ParsedSpec(BaseModel):
    """A fully parsed spec pack with all artifacts loaded.

    Combines the lightweight ``SpecMeta`` discovery metadata with the
    parsed JSON artifacts (requirements, test_spec, tasks) and the raw
    PRD markdown text.

    Attributes:
        meta: Discovery metadata (ID, name, status, path).
        requirements: Parsed ``requirements.json`` model.
        test_spec: Parsed ``test_spec.json`` model.
        tasks: Parsed ``tasks.json`` model.
        prd_text: Raw markdown content of ``prd.md`` (empty string if
            the file was missing).
    """

    model_config = ConfigDict(frozen=True)

    meta: SpecMeta
    requirements: Requirements
    test_spec: TestSpec
    tasks: Tasks
    prd_text: str


class ExecutionPlan(BaseModel):
    """An ordered plan of spec packs ready for sequential implementation.

    The specs list is topologically sorted so that every dependency is
    implemented before its dependent. The model is frozen and serializable
    to JSON for debugging and logging.

    Attributes:
        specs: Ordered list of parsed specs for implementation.
        count: Total number of specs in the plan.
        timestamp: ISO 8601 creation timestamp.
    """

    model_config = ConfigDict(frozen=True)

    specs: list[ParsedSpec]
    count: int
    timestamp: str
