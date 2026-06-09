"""SpecAgent -- core agent wrapping the Anthropic client for spec operations.

Provides async methods for PRD assessment, refinement, and artifact
generation using the Anthropic messages API with tool use for structured
output.  Handles retry logic with exponential backoff for transient errors.

Requirements: 03-REQ-1.*, 03-REQ-2.*, 03-REQ-3.*, 03-REQ-5.*
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from anthropic import (
    APIConnectionError,
    APIStatusError,
    InternalServerError,
    RateLimitError,
)

from speclib.errors import AgentError
from speclib.prompts import assessment_system_prompt, assessment_user_prompt
from speclib.session import Assessment, Question
from speclib.tools import assessment_tools

logger = logging.getLogger(__name__)

# Retry configuration (03-REQ-5.1, 03-REQ-5.E2)
_MAX_RETRIES = 3
_BASE_DELAY = 1.0  # seconds
_MAX_CUMULATIVE_WAIT = 30.0  # seconds


def validate_artifact(artifact_name: str, content: dict[str, Any]) -> None:
    """Validate an artifact against its afspec JSON schema.

    This is a module-level function so it can be patched in tests.
    Called by ``generate_artifacts`` after each artifact is produced.

    Raises:
        Exception: If the artifact fails schema validation.
    """
    import afspec  # type: ignore[import-untyped]

    afspec.validate_artifact(artifact_name, content)


class SpecAgent:
    """Core agent wrapping the Anthropic client for spec operations."""

    def __init__(self, client: object, model: str) -> None:
        """Initialize with an Anthropic client and model name.

        Args:
            client: An Anthropic client instance (Anthropic,
                AnthropicBedrock, or AnthropicVertex).
            model: The model identifier for API calls.
        """
        self._client = client
        self._model = model

    # -- public methods ---------------------------------------------------

    async def assess_prd(self, prd_text: str, spec_name: str) -> Assessment:
        """Send PRD to agent for assessment.

        Validates the input, sends the PRD to the Anthropic messages API
        with the assessment prompt and tool definition, then parses and
        returns the structured Assessment.

        Args:
            prd_text: The PRD markdown text to assess.
            spec_name: The name of the spec being assessed.

        Returns:
            An ``Assessment`` with quality, summary, gaps, and questions.

        Raises:
            AgentError: If *prd_text* is empty, the API call fails
                permanently, or the response cannot be parsed.
        """
        if not prd_text or not prd_text.strip():
            raise AgentError("PRD text must not be empty")

        system = assessment_system_prompt()
        user_msg = assessment_user_prompt(prd_text, spec_name)
        messages: list[dict[str, str]] = [
            {"role": "user", "content": user_msg},
        ]
        tools = assessment_tools()

        response = await self._call_api(messages, tools, system=system)
        tool_input = self._extract_tool_call(response, "submit_assessment")
        return self._parse_assessment(tool_input)

    async def refine_prd(
        self,
        prd_text: str,
        answers: dict[str, str],
        previous_assessment: Assessment,
    ) -> tuple[str, Assessment]:
        """Send answers, get updated PRD and new assessment.

        Stub: full implementation provided in task group 6.
        """
        raise NotImplementedError(
            "refine_prd not yet implemented (task group 6)"
        )

    async def generate_artifacts(
        self,
        prd_text: str,
        spec_id: str,
        spec_name: str,
    ) -> dict[str, Any]:
        """Generate requirements, test_spec, and tasks content.

        Stub: full implementation provided in task group 6.
        """
        raise NotImplementedError(
            "generate_artifacts not yet implemented (task group 6)"
        )

    # -- internal methods -------------------------------------------------

    async def _call_api(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        system: str | None = None,
    ) -> Any:
        """Send messages to the Anthropic API with retry logic.

        Retries up to 3 times on HTTP 429, 5xx, and connection errors
        using exponential backoff (1 s, 2 s, 4 s).  Raises ``AgentError``
        immediately on non-retryable 4xx errors.

        Args:
            messages: The conversation messages to send.
            tools: Tool definitions for structured output.
            system: Optional system prompt.

        Returns:
            The API response message.

        Raises:
            AgentError: On permanent failure or exhausted retries.
                The original exception is set as ``__cause__``.
        """
        cumulative_wait = 0.0
        last_error: Exception | None = None

        for attempt in range(_MAX_RETRIES + 1):
            try:
                kwargs: dict[str, Any] = {
                    "model": self._model,
                    "max_tokens": 4096,
                    "messages": messages,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = {"type": "any"}
                if system is not None:
                    kwargs["system"] = system

                response = await self._client.messages.create(**kwargs)  # type: ignore[attr-defined]
                logger.debug(
                    "API call succeeded on attempt %d", attempt + 1
                )
                return response

            except (
                RateLimitError,
                InternalServerError,
                APIConnectionError,
            ) as exc:
                last_error = exc
                logger.debug(
                    "Transient API error on attempt %d: %s",
                    attempt + 1,
                    exc,
                )
                if attempt < _MAX_RETRIES:
                    delay = _BASE_DELAY * (2**attempt)
                    if cumulative_wait + delay > _MAX_CUMULATIVE_WAIT:
                        logger.debug(
                            "Cumulative wait %.1fs + delay %.1fs exceeds "
                            "%.1fs cap; abandoning retries",
                            cumulative_wait,
                            delay,
                            _MAX_CUMULATIVE_WAIT,
                        )
                        break
                    cumulative_wait += delay
                    await asyncio.sleep(delay)

            except APIStatusError as exc:
                # Non-retryable HTTP error (4xx other than 429)
                logger.debug(
                    "Non-retryable API error (HTTP %d): %s",
                    exc.status_code,
                    exc,
                )
                raise AgentError(
                    f"API error (HTTP {exc.status_code}): {exc}"
                ) from exc

        raise AgentError(
            f"API call failed after {_MAX_RETRIES + 1} attempts"
        ) from last_error

    def _extract_tool_call(
        self,
        response: Any,
        tool_name: str,
    ) -> dict[str, Any]:
        """Extract the input dict from a tool_use content block.

        Searches the response content blocks for a ``tool_use`` block
        with the given name and returns its ``input`` dict.

        Args:
            response: The API response message.
            tool_name: The expected tool name to find.

        Returns:
            The tool input dict.

        Raises:
            AgentError: If the tool was not called or the response
                contains no matching tool_use blocks.
        """
        for block in response.content:
            if (
                getattr(block, "type", None) == "tool_use"
                and getattr(block, "name", None) == tool_name
            ):
                return block.input  # type: ignore[no-any-return]

        raise AgentError(
            f"Model did not produce structured output: "
            f"tool '{tool_name}' was not called"
        )

    def _parse_assessment(self, tool_input: dict[str, Any]) -> Assessment:
        """Validate and construct an Assessment from tool input.

        Enforces the quality enum, required fields, and the invariant
        that non-ready assessments must include questions.

        Args:
            tool_input: The raw dict from the submit_assessment
                tool call.

        Returns:
            A validated ``Assessment`` instance.

        Raises:
            AgentError: If required fields are missing or invalid.
        """
        # Validate quality enum (03-REQ-1.2)
        valid_qualities = {"ready", "needs_refinement", "incomplete"}
        quality = tool_input.get("quality")
        if quality not in valid_qualities:
            raise AgentError(
                f"Invalid quality value: {quality!r}; "
                f"expected one of {sorted(valid_qualities)}"
            )

        # Validate required fields (03-REQ-1.E2)
        missing = [
            f
            for f in ("summary", "gaps", "questions")
            if f not in tool_input
        ]
        if missing:
            raise AgentError(
                f"Assessment is missing required fields: "
                f"{', '.join(missing)}"
            )

        summary: str = tool_input["summary"]
        gaps: list[str] = tool_input["gaps"]
        questions_data: list[dict[str, Any]] = tool_input["questions"]

        # Non-ready assessments must have questions (03-REQ-1.5)
        if quality != "ready" and not questions_data:
            raise AgentError(
                f"Assessment with quality {quality!r} must include "
                f"at least one question"
            )

        # Build Question objects
        questions = [
            Question(
                id=q["id"],
                text=q["text"],
                context=q["context"],
                options=q.get("options", []),
                required=q.get("required", False),
            )
            for q in questions_data
        ]

        return Assessment(
            quality=quality,
            summary=summary,
            gaps=gaps,
            questions=questions,
        )
