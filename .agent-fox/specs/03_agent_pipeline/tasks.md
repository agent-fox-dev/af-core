# Implementation Plan: Agent Pipeline

<!-- AGENT INSTRUCTIONS
- Implement exactly ONE top-level task group per session
- Task group 1 writes failing tests from test_spec.md — all subsequent groups
  implement code to make those tests pass
- Follow the git-flow: feature branch from develop -> implement -> test -> merge to develop
- Update checkbox states as you go: [-] in progress, [x] complete
-->

## Overview

This plan implements the agent pipeline for speclib: the SpecAgent class,
prompt templates, tool definitions, error handling with retries, and session
integration. Groups are ordered so tests exist before implementation, and
foundational modules (errors, tools, prompts) exist before the agent class
that depends on them.

## Dependencies

This spec depends on:
- **Spec 01, group 3** — `speclib.auth.create_client()`, `speclib.errors.SpeclibError`
- **Spec 02, group 2** — `SpecSession`, `Assessment`, `Question`, `SessionState`

These must be implemented before task group 3 of this spec.

## Test Commands

- Spec tests: `uv run pytest -q tests/test_agent.py tests/test_prompts.py tests/test_tools.py tests/test_session_agent.py`
- Unit tests: `uv run pytest -q tests/`
- Property tests: `uv run pytest -q tests/ -k property`
- All tests: `uv run pytest -q`
- Linter: `uv run ruff check && uv run mypy speclib/`

## Tasks

- [ ] 1. Write failing spec tests
  - [ ] 1.1 Set up test file structure
    - Create `tests/test_agent.py` for SpecAgent tests (TS-03-1 through TS-03-14)
    - Create `tests/test_prompts.py` for prompt template tests (TS-03-15 through TS-03-17)
    - Create `tests/test_tools.py` for tool definition tests (TS-03-18 through TS-03-20)
    - Create `tests/test_session_agent.py` for session integration tests (TS-03-27 through TS-03-31)
    - Create `tests/conftest_agent.py` with shared fixtures for mocked Anthropic client and responses
    - _Test Spec: TS-03-1 through TS-03-31_

  - [ ] 1.2 Translate acceptance-criterion tests for agent
    - One test function per TS-03-{N} entry for N in 1..14
    - Build mock Anthropic client fixtures that return tool_use responses
    - Tests MUST fail (modules don't exist yet)
    - _Test Spec: TS-03-1 through TS-03-14_

  - [ ] 1.3 Translate prompt and tool tests
    - One test function per TS-03-{N} entry for N in 15..20
    - Verify prompt content and tool schema structure
    - _Test Spec: TS-03-15 through TS-03-20_

  - [ ] 1.4 Translate retry and error handling tests
    - TS-03-21 through TS-03-26
    - Build mock clients that raise various API exceptions
    - _Test Spec: TS-03-21 through TS-03-26_

  - [ ] 1.5 Translate session integration tests
    - TS-03-27 through TS-03-31
    - Tests for session.assess(), session.refine(), session.generate()
    - _Test Spec: TS-03-27 through TS-03-31_

  - [ ] 1.6 Translate edge-case tests
    - One test function per TS-03-E{N} entry
    - _Test Spec: TS-03-E1 through TS-03-E14_

  - [ ] 1.7 Translate property tests
    - One property test per TS-03-P{N} entry using hypothesis
    - _Test Spec: TS-03-P1 through TS-03-P5_

  - [ ] 1.8 Write integration smoke tests
    - TS-03-SMOKE-1 (full assessment flow)
    - TS-03-SMOKE-2 (full refinement flow)
    - TS-03-SMOKE-3 (full generation flow)
    - TS-03-SMOKE-4 (retry and recovery)
    - _Test Spec: TS-03-SMOKE-1 through TS-03-SMOKE-4_

  - [ ] 1.V Verify task group 1
    - [ ] All spec tests exist and are syntactically valid
    - [ ] All spec tests FAIL (red) -- no implementation yet
    - [ ] No linter warnings introduced: `uv run ruff check tests/`

- [ ] 2. Implement error type and tool definitions
  - [ ] 2.1 Add AgentError to speclib/errors.py
    - `AgentError(SpeclibError)` with `detail` attribute
    - _Requirements: 03-REQ-5.4_

  - [ ] 2.2 Implement speclib/tools.py
    - `SUBMIT_ASSESSMENT_TOOL` constant with full JSON schema
    - `SUBMIT_PRD_UPDATE_TOOL` constant with full JSON schema
    - `SUBMIT_ARTIFACT_TOOL` constant with full JSON schema
    - `assessment_tools()` function returning `[SUBMIT_ASSESSMENT_TOOL]`
    - `refinement_tools()` function returning `[SUBMIT_PRD_UPDATE_TOOL, SUBMIT_ASSESSMENT_TOOL]`
    - `artifact_tool(artifact_name)` function returning `[SUBMIT_ARTIFACT_TOOL]`
    - _Requirements: 03-REQ-4.4, 03-REQ-4.5, 03-REQ-4.6_

  - [ ] 2.V Verify task group 2
    - [ ] Tool definition tests pass: `uv run pytest -q tests/test_tools.py`
    - [ ] AgentError test passes: `uv run pytest -q tests/test_agent.py -k test_agent_error`
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings introduced: `uv run ruff check speclib/`

- [ ] 3. Implement prompt templates
  - [ ] 3.1 Implement speclib/prompts.py
    - `assessment_system_prompt()` -- system prompt referencing Intent, Goals, Non-Goals, Background
    - `assessment_user_prompt(prd_text, spec_name)` -- formats PRD text for assessment
    - `refinement_system_prompt()` -- system prompt for incorporating answers
    - `refinement_user_prompt(prd_text, answers, previous_assessment)` -- formats PRD, answers, prior assessment
    - `generation_system_prompt()` -- system prompt for JSON artifact production
    - `generation_user_prompt(prd_text, artifact_name, prior_artifacts)` -- formats for single artifact generation
    - All functions validate required parameters, raising ValueError for empty inputs
    - _Requirements: 03-REQ-4.1, 03-REQ-4.2, 03-REQ-4.3, 03-REQ-4.E1_

  - [ ] 3.V Verify task group 3
    - [ ] Prompt tests pass: `uv run pytest -q tests/test_prompts.py`
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings introduced: `uv run ruff check speclib/prompts.py`

- [ ] 4. Implement SpecAgent core
  - [ ] 4.1 Implement speclib/agent.py -- SpecAgent.__init__
    - Store client and model
    - _Requirements: none (structural)_

  - [ ] 4.2 Implement SpecAgent._call_api
    - Async method calling client.messages.create
    - Retry logic: catch 429/5xx/connection errors
    - Exponential backoff: 1s, 2s, 4s (max 3 retries)
    - Cumulative wait cap at 30 seconds
    - Wrap permanent failures in AgentError with __cause__
    - _Requirements: 03-REQ-5.1, 03-REQ-5.2, 03-REQ-5.3, 03-REQ-5.E1, 03-REQ-5.E2_

  - [ ] 4.3 Implement SpecAgent._extract_tool_call
    - Find tool_use content block by tool name
    - Raise AgentError if not found
    - Return the tool input dict
    - _Requirements: 03-REQ-1.E3, 03-REQ-5.5_

  - [ ] 4.4 Implement SpecAgent._parse_assessment
    - Validate required fields: quality, summary, gaps, questions
    - Validate quality enum
    - Validate non-ready assessments have questions
    - Build Assessment and Question objects
    - _Requirements: 03-REQ-1.2, 03-REQ-1.3, 03-REQ-1.4, 03-REQ-1.5, 03-REQ-1.6, 03-REQ-1.E2_

  - [ ] 4.5 Implement SpecAgent.assess_prd
    - Validate prd_text not empty
    - Build messages using prompt templates
    - Call _call_api with assessment_tools
    - Extract and parse assessment
    - _Requirements: 03-REQ-1.1, 03-REQ-1.E1_

  - [ ] 4.6 Implement SpecAgent.refine_prd
    - Validate answers not empty
    - Validate answer IDs match assessment questions
    - Build messages using refinement prompts
    - Call _call_api with refinement_tools
    - Extract PRD update and new assessment
    - Return (updated_prd, new_assessment)
    - _Requirements: 03-REQ-2.1, 03-REQ-2.2, 03-REQ-2.3, 03-REQ-2.4, 03-REQ-2.5, 03-REQ-2.E1, 03-REQ-2.E2, 03-REQ-2.E3_

  - [ ] 4.7 Implement SpecAgent.generate_artifacts
    - Validate prd_text not empty
    - Loop through ["requirements", "test_spec", "tasks"]
    - For each: build messages with prior artifacts as context, call API, extract, validate
    - Abort on validation failure
    - Return dict of artifact name to parsed JSON
    - _Requirements: 03-REQ-3.1, 03-REQ-3.2, 03-REQ-3.3, 03-REQ-3.4, 03-REQ-3.5, 03-REQ-3.6, 03-REQ-3.7, 03-REQ-3.E1, 03-REQ-3.E2, 03-REQ-3.E3_

  - [ ] 4.V Verify task group 4
    - [ ] Agent unit tests pass: `uv run pytest -q tests/test_agent.py`
    - [ ] Retry tests pass: `uv run pytest -q tests/test_agent.py -k retry`
    - [ ] Edge case tests pass: `uv run pytest -q tests/test_agent.py -k edge`
    - [ ] Property tests pass: `uv run pytest -q tests/ -k property`
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check && uv run mypy speclib/agent.py`

- [ ] 5. Wire agent into SpecSession
  - [ ] 5.1 Implement SpecSession.assess()
    - Create SpecAgent via create_client()
    - Call assess_prd() with PRD text from prd.md
    - Persist Assessment to _session.json (append to assessment_history)
    - Transition state to "assessing"
    - On AgentError: do not transition, persist error, re-raise
    - _Requirements: 03-REQ-6.1, 03-REQ-6.4, 03-REQ-6.5_

  - [ ] 5.2 Implement SpecSession.refine()
    - Create SpecAgent via create_client()
    - Call refine_prd() with PRD text, answers, and last Assessment
    - Update prd.md with returned text
    - Persist new Assessment to _session.json
    - Transition state appropriately
    - On AgentError: do not transition, persist error, re-raise
    - _Requirements: 03-REQ-6.2, 03-REQ-6.4, 03-REQ-6.5_

  - [ ] 5.3 Implement SpecSession.generate()
    - Create SpecAgent via create_client()
    - Detect existing artifacts (for resume after partial failure)
    - Call generate_artifacts() (or partial generation for missing ones)
    - Write each artifact JSON to spec directory
    - Run cross-file validation via afspec
    - Transition state to "generated"
    - On AgentError: keep partial artifacts, stay in "generating", re-raise
    - _Requirements: 03-REQ-6.3, 03-REQ-6.4, 03-REQ-6.E1, 03-REQ-6.E2_

  - [ ] 5.V Verify task group 5
    - [ ] Session integration tests pass: `uv run pytest -q tests/test_session_agent.py`
    - [ ] Edge case tests pass: `uv run pytest -q tests/test_session_agent.py -k edge`
    - [ ] Property tests pass: `uv run pytest -q tests/ -k property`
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings: `uv run ruff check && uv run mypy speclib/`

- [ ] 6. Wiring verification

  - [ ] 6.1 Trace every execution path from design.md end-to-end
    - Path 1: session.assess() -> SpecAgent.assess_prd -> prompts -> tools -> API -> parse -> persist
    - Path 2: session.refine() -> SpecAgent.refine_prd -> prompts -> tools -> API -> parse -> persist
    - Path 3: session.generate() -> SpecAgent.generate_artifacts -> (loop: prompt -> tool -> API -> validate) -> write files
    - Path 4: transient error -> retry -> backoff -> success or AgentError
    - Verify each function in the chain is actually called by the previous one
    - _Requirements: all_

  - [ ] 6.2 Verify return values propagate correctly
    - assess_prd returns Assessment consumed by session.assess
    - refine_prd returns (str, Assessment) consumed by session.refine
    - generate_artifacts returns dict consumed by session.generate for file writing
    - _Requirements: all_

  - [ ] 6.3 Run the integration smoke tests
    - All TS-03-SMOKE-* tests pass with mocked Anthropic client
    - _Test Spec: TS-03-SMOKE-1 through TS-03-SMOKE-4_

  - [ ] 6.4 Stub / dead-code audit
    - Search speclib/agent.py, speclib/prompts.py, speclib/tools.py for `return []`, `return None` on non-Optional returns, `pass`, `# TODO`, `NotImplementedError`
    - Each hit must be justified or replaced
    - _Requirements: all_

  - [ ] 6.5 Cross-spec entry point verification
    - Verify `SpecSession.assess()` calls `create_client()` from spec 01
    - Verify `SpecSession.assess/refine/generate()` delegate to `SpecAgent` methods
    - Verify `Assessment` and `Question` types from spec 02 are used correctly
    - Verify `afspec.validate_artifact()` is called during generation
    - _Requirements: all_

  - [ ] 6.V Verify wiring group
    - [ ] All smoke tests pass
    - [ ] No unjustified stubs remain in speclib/agent.py, speclib/prompts.py, speclib/tools.py
    - [ ] All execution paths from design.md are live
    - [ ] All existing tests still pass: `uv run pytest -q`

## Traceability

| Requirement | Test Spec Entry | Implemented By Task | Verified By Test |
|-------------|-----------------|---------------------|------------------|
| 03-REQ-1.1 | TS-03-1 | 4.5 | tests/test_agent.py::test_assess_prd_returns_assessment |
| 03-REQ-1.2 | TS-03-1 | 4.4, 4.5 | tests/test_agent.py::test_assess_prd_valid_quality |
| 03-REQ-1.3 | TS-03-2 | 4.4 | tests/test_agent.py::test_assessment_summary |
| 03-REQ-1.4 | TS-03-3 | 4.4 | tests/test_agent.py::test_assessment_gaps |
| 03-REQ-1.5 | TS-03-4 | 4.4 | tests/test_agent.py::test_non_ready_has_questions |
| 03-REQ-1.6 | TS-03-5 | 4.4 | tests/test_agent.py::test_ready_empty_questions |
| 03-REQ-1.E1 | TS-03-E1 | 4.5 | tests/test_agent.py::test_empty_prd_assess |
| 03-REQ-1.E2 | TS-03-E2 | 4.4 | tests/test_agent.py::test_malformed_assessment |
| 03-REQ-1.E3 | TS-03-E3 | 4.3 | tests/test_agent.py::test_no_tool_use |
| 03-REQ-2.1 | TS-03-6 | 4.6 | tests/test_agent.py::test_refine_prd_returns_tuple |
| 03-REQ-2.2 | TS-03-6 | 4.6 | tests/test_agent.py::test_refine_prd_returns_tuple |
| 03-REQ-2.3 | TS-03-7 | 4.6 | tests/test_agent.py::test_refine_answers_dict |
| 03-REQ-2.4 | TS-03-8 | 4.6 | tests/test_agent.py::test_refine_preserves_frontmatter |
| 03-REQ-2.5 | TS-03-6 | 4.6 | tests/test_agent.py::test_refine_prd_returns_tuple |
| 03-REQ-2.E1 | TS-03-E4 | 4.6 | tests/test_agent.py::test_empty_answers |
| 03-REQ-2.E2 | TS-03-E5 | 4.6 | tests/test_agent.py::test_unrecognized_question_ids |
| 03-REQ-2.E3 | TS-03-E6 | 4.6 | tests/test_agent.py::test_missing_assessment_in_refinement |
| 03-REQ-3.1 | TS-03-9 | 4.7 | tests/test_agent.py::test_generate_three_artifacts |
| 03-REQ-3.2 | TS-03-9 | 4.7 | tests/test_agent.py::test_generate_three_artifacts |
| 03-REQ-3.3 | TS-03-10 | 4.7 | tests/test_agent.py::test_generate_returns_parsed_json |
| 03-REQ-3.4 | TS-03-11 | 4.7 | tests/test_agent.py::test_validate_before_next |
| 03-REQ-3.5 | TS-03-12 | 4.7 | tests/test_agent.py::test_validation_failure_aborts |
| 03-REQ-3.6 | TS-03-13 | 4.7 | tests/test_agent.py::test_test_spec_includes_requirements |
| 03-REQ-3.7 | TS-03-14 | 4.7 | tests/test_agent.py::test_tasks_includes_both_prior |
| 03-REQ-3.E1 | TS-03-E7 | 4.7 | tests/test_agent.py::test_empty_prd_generate |
| 03-REQ-3.E2 | TS-03-E8 | 4.7 | tests/test_agent.py::test_artifact_tool_not_invoked |
| 03-REQ-3.E3 | TS-03-E9 | 4.7 | tests/test_agent.py::test_schema_validation_error_detail |
| 03-REQ-4.1 | TS-03-15 | 3.1 | tests/test_prompts.py::test_assessment_prompt |
| 03-REQ-4.2 | TS-03-16 | 3.1 | tests/test_prompts.py::test_refinement_prompt |
| 03-REQ-4.3 | TS-03-17 | 3.1 | tests/test_prompts.py::test_generation_prompt |
| 03-REQ-4.4 | TS-03-18, TS-03-19, TS-03-20 | 2.2 | tests/test_tools.py::test_assessment_tool, test_refinement_tools, test_artifact_tool |
| 03-REQ-4.5 | TS-03-18, TS-03-19, TS-03-20 | 2.2 | tests/test_tools.py::test_assessment_tool, test_refinement_tools, test_artifact_tool |
| 03-REQ-4.6 | TS-03-18 | 2.2 | tests/test_tools.py::test_assessment_tool_schema |
| 03-REQ-4.E1 | TS-03-E10 | 3.1 | tests/test_prompts.py::test_missing_parameter |
| 03-REQ-5.1 | TS-03-21, TS-03-22 | 4.2 | tests/test_agent.py::test_retry_429, test_retry_5xx |
| 03-REQ-5.2 | TS-03-23 | 4.2 | tests/test_agent.py::test_retry_exhaustion |
| 03-REQ-5.3 | TS-03-24 | 4.2 | tests/test_agent.py::test_no_retry_4xx |
| 03-REQ-5.4 | TS-03-25 | 2.1 | tests/test_agent.py::test_agent_error_hierarchy |
| 03-REQ-5.5 | TS-03-26 | 4.3 | tests/test_agent.py::test_unparseable_response |
| 03-REQ-5.E1 | TS-03-E11 | 4.2 | tests/test_agent.py::test_timeout_retry |
| 03-REQ-5.E2 | TS-03-E12 | 4.2 | tests/test_agent.py::test_cumulative_wait_cap |
| 03-REQ-6.1 | TS-03-27 | 5.1 | tests/test_session_agent.py::test_session_assess |
| 03-REQ-6.2 | TS-03-28 | 5.2 | tests/test_session_agent.py::test_session_refine |
| 03-REQ-6.3 | TS-03-29 | 5.3 | tests/test_session_agent.py::test_session_generate |
| 03-REQ-6.4 | TS-03-30 | 5.1, 5.2, 5.3 | tests/test_session_agent.py::test_error_no_transition |
| 03-REQ-6.5 | TS-03-31 | 5.1, 5.2 | tests/test_session_agent.py::test_assessment_history |
| 03-REQ-6.E1 | TS-03-E13 | 5.3 | tests/test_session_agent.py::test_partial_generation |
| 03-REQ-6.E2 | TS-03-E14 | 5.3 | tests/test_session_agent.py::test_resume_partial |
| Property 1 | TS-03-P1 | 4.4 | tests/test_agent.py::test_property_quality_enum |
| Property 2 | TS-03-P2 | 4.4 | tests/test_agent.py::test_property_non_ready_questions |
| Property 3 | TS-03-P3 | 4.7 | tests/test_agent.py::test_property_generation_order |
| Property 4 | TS-03-P4 | 4.2 | tests/test_agent.py::test_property_retry_bound |
| Property 5 | TS-03-P5 | 5.3 | tests/test_session_agent.py::test_property_partial_artifacts |
| Path 1 | TS-03-SMOKE-1 | 5.1 | tests/test_session_agent.py::test_smoke_assessment |
| Path 2 | TS-03-SMOKE-2 | 5.2 | tests/test_session_agent.py::test_smoke_refinement |
| Path 3 | TS-03-SMOKE-3 | 5.3 | tests/test_session_agent.py::test_smoke_generation |
| Path 4 | TS-03-SMOKE-4 | 4.2, 5.1 | tests/test_session_agent.py::test_smoke_retry_recovery |
