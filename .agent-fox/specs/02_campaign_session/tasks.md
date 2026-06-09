# Implementation Plan: Campaign Management and Spec Authoring Session Model

<!-- AGENT INSTRUCTIONS
- Implement exactly ONE top-level task group per session
- Task group 1 writes failing tests from test_spec.md — all subsequent groups
  implement code to make those tests pass
- Follow the git-flow: feature branch from develop -> implement -> test -> merge to develop
- Update checkbox states as you go: [-] in progress, [x] complete
-->

## Overview

This plan implements the campaign directory management and spec authoring
session model. Group 1 writes all failing tests. Groups 2-4 implement the
production code to make those tests pass. Group 5 verifies wiring
end-to-end. This spec depends on spec 01 (group 2) for the package
structure and error hierarchy (`SpeclibError`).

## Test Commands

- Spec tests: `uv run pytest -q tests/test_campaign.py tests/test_session.py`
- Unit tests: `uv run pytest -q tests/`
- Property tests: `uv run pytest -q tests/ -k property`
- Smoke tests: `uv run pytest -q tests/ -k smoke`
- All tests: `uv run pytest -q`
- Linter: `uv run ruff check && uv run mypy speclib/`

## Tasks

- [ ] 1. Write failing spec tests
  - [ ] 1.1 Create test files and fixtures
    - Create `tests/test_campaign.py` for campaign tests (TS-02-1 through TS-02-9, TS-02-E1 through TS-02-E6, TS-02-P3, TS-02-P4)
    - Create `tests/test_session.py` for session tests (TS-02-10 through TS-02-19, TS-02-E7 through TS-02-E11, TS-02-P1, TS-02-P2, TS-02-P5, TS-02-P6)
    - Add fixtures to `tests/conftest.py`: `tmp_campaign_dir`, `campaign`, `session`, `session_with_artifacts`
    - _Test Spec: TS-02-1 through TS-02-19_

  - [ ] 1.2 Translate campaign acceptance-criterion tests
    - `test_campaign_create` (TS-02-1)
    - `test_campaign_create_fails_existing` (TS-02-2)
    - `test_campaign_yaml_fields` (TS-02-3)
    - `test_campaign_open` (TS-02-4)
    - `test_campaign_specs_sorted` (TS-02-5)
    - `test_new_spec_string_prd` (TS-02-6)
    - `test_new_spec_path_prd` (TS-02-7)
    - `test_spec_dir_sequential_prefixes` (TS-02-8)
    - `test_prd_frontmatter` (TS-02-9)
    - _Test Spec: TS-02-1 through TS-02-9_

  - [ ] 1.3 Translate session acceptance-criterion tests
    - `test_session_state_enum` (TS-02-10)
    - `test_legal_state_transitions` (TS-02-11)
    - `test_illegal_transition_error_message` (TS-02-12)
    - `test_accept_prd_from_assessing_and_refining` (TS-02-13)
    - `test_state_persisted_on_transition` (TS-02-14)
    - `test_session_resume` (TS-02-15)
    - `test_session_json_fields` (TS-02-16)
    - `test_validate_with_artifacts` (TS-02-17)
    - `test_render_combined` (TS-02-18)
    - `test_render_individual` (TS-02-19)
    - _Test Spec: TS-02-10 through TS-02-19_

  - [ ] 1.4 Translate edge-case tests
    - `test_create_non_empty_non_campaign` (TS-02-E1)
    - `test_create_parent_missing` (TS-02-E2)
    - `test_open_no_campaign_yaml` (TS-02-E3)
    - `test_open_invalid_yaml` (TS-02-E4)
    - `test_new_spec_invalid_name` (TS-02-E5)
    - `test_new_spec_nonexistent_prd_path` (TS-02-E6)
    - `test_generate_from_wrong_state` (TS-02-E7)
    - `test_assess_from_generated` (TS-02-E8)
    - `test_resume_no_session_json` (TS-02-E9)
    - `test_resume_invalid_json` (TS-02-E10)
    - `test_validate_render_missing_artifacts` (TS-02-E11)
    - _Test Spec: TS-02-E1 through TS-02-E11_

  - [ ] 1.5 Translate property tests
    - `test_property_state_machine_total` (TS-02-P1) — hypothesis over states and methods
    - `test_property_persistence_idempotent` (TS-02-P2)
    - `test_property_numbering_monotonic` (TS-02-P3)
    - `test_property_create_atomic` (TS-02-P4)
    - `test_property_artifacts_required` (TS-02-P5)
    - `test_property_accept_prd_states` (TS-02-P6)
    - _Test Spec: TS-02-P1 through TS-02-P6_

  - [ ] 1.6 Write integration smoke tests
    - `test_smoke_campaign_to_spec_creation` (TS-02-SMOKE-1)
    - `test_smoke_open_and_list_specs` (TS-02-SMOKE-2)
    - `test_smoke_session_lifecycle` (TS-02-SMOKE-3)
    - `test_smoke_session_resume` (TS-02-SMOKE-4)
    - `test_smoke_validate_and_render` (TS-02-SMOKE-5)
    - _Test Spec: TS-02-SMOKE-1 through TS-02-SMOKE-5_

  - [ ] 1.V Verify task group 1
    - [ ] All spec tests exist and are syntactically valid
    - [ ] All spec tests FAIL (red) — no implementation yet
    - [ ] No linter warnings introduced: `uv run ruff check tests/`

- [ ] 2. Implement error types and data models
  - [ ] 2.1 Add CampaignError and SessionError to speclib/errors.py
    - `CampaignError(SpeclibError)` — campaign directory operation failures
    - `SessionError(SpeclibError)` — session state machine or persistence failures
    - _Requirements: 02-REQ-4.3, 02-REQ-1.2, 02-REQ-2.E1_

  - [ ] 2.2 Create speclib/session.py — data models only
    - `SessionState` enum with six values
    - `Question` dataclass
    - `Assessment` dataclass
    - `RepairSuggestion` dataclass
    - `ValidationResult` dataclass
    - `GenerateResult` dataclass
    - _Requirements: 02-REQ-4.1, 02-REQ-5.3_

  - [ ] 2.3 Create speclib/campaign.py — CampaignMetadata only
    - `CampaignMetadata` dataclass with name, description, created_at, updated_at
    - _Requirements: 02-REQ-1.3_

  - [ ] 2.4 Update speclib/__init__.py with new exports
    - Export: `CampaignError`, `SessionError`, `SessionState`, `Campaign`, `SpecSession`
    - Export data types: `CampaignMetadata`, `Assessment`, `Question`, `ValidationResult`, `GenerateResult`, `RepairSuggestion`
    - _Requirements: all_

  - [ ] 2.V Verify task group 2
    - [ ] SessionState enum test passes (TS-02-10)
    - [ ] Error type tests pass (import and isinstance checks)
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings introduced: `uv run ruff check`

- [ ] 3. Implement Campaign class
  - [ ] 3.1 Implement Campaign.create()
    - Validate path: parent must exist, target must be empty or non-existent
    - Create directory if needed
    - Write campaign.yaml with CampaignMetadata
    - Return Campaign instance
    - _Requirements: 02-REQ-1.1, 02-REQ-1.2, 02-REQ-1.E1, 02-REQ-1.E2_

  - [ ] 3.2 Implement Campaign.open()
    - Check campaign.yaml exists
    - Parse YAML into CampaignMetadata
    - Handle invalid YAML with CampaignError
    - Return Campaign instance
    - _Requirements: 02-REQ-2.1, 02-REQ-2.E1, 02-REQ-2.E2_

  - [ ] 3.3 Implement campaign.specs()
    - Scan directory for `{NN}_{snake_case}` pattern
    - Sort by numeric prefix
    - Exclude `archive/`, `_session.json`, non-matching entries
    - Return list of Path objects
    - _Requirements: 02-REQ-2.2_

  - [ ] 3.4 Implement campaign.new_spec()
    - Validate spec_name against `[a-z][a-z0-9_]*`
    - Compute next numeric prefix
    - Create spec directory
    - Write prd.md (from string with frontmatter, or copy from Path)
    - Write initial _session.json
    - Update campaign.yaml updated_at
    - Return SpecSession instance
    - _Requirements: 02-REQ-3.1, 02-REQ-3.2, 02-REQ-3.3, 02-REQ-3.4, 02-REQ-3.E1, 02-REQ-3.E2_

  - [ ] 3.5 Implement campaign.path and campaign.metadata properties
    - _Requirements: 02-REQ-1.1, 02-REQ-2.1_

  - [ ] 3.V Verify task group 3
    - [ ] Campaign tests pass: `uv run pytest -q tests/test_campaign.py`
    - [ ] Campaign edge case tests pass (TS-02-E1 through TS-02-E6)
    - [ ] Campaign property tests pass (TS-02-P3, TS-02-P4)
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings introduced: `uv run ruff check && uv run mypy speclib/`

- [ ] 4. Implement SpecSession class
  - [ ] 4.1 Implement session state machine core
    - Define legal transitions as a dict/set
    - Implement `_transition(target_state)` method that checks legality and persists
    - Raise SessionError with current and required state on illegal transitions
    - _Requirements: 02-REQ-4.2, 02-REQ-4.3_

  - [ ] 4.2 Implement session persistence
    - `_persist()` method: atomically write _session.json
    - Include state, prd_path, assessment_history, qa_exchanges, generated_artifacts, mode
    - Call _persist() on every state transition
    - _Requirements: 02-REQ-5.1, 02-REQ-5.3_

  - [ ] 4.3 Implement SpecSession.resume()
    - Read _session.json
    - Deserialize state, history, exchanges
    - Handle missing file (SessionError)
    - Handle invalid JSON (SessionError with parse detail)
    - Return SpecSession in persisted state
    - _Requirements: 02-REQ-5.2, 02-REQ-5.E1, 02-REQ-5.E2_

  - [ ] 4.4 Implement session methods (stubs and non-stubs)
    - `assess()`: check state allows transition init->assessing, then raise NotImplementedError
    - `refine(answers)`: check state allows transition assessing->refining, then raise NotImplementedError
    - `accept_prd()`: check state is assessing or refining, transition to prd_accepted
    - `generate()`: check state is prd_accepted, transition to generating, then raise NotImplementedError
    - `validate()`: check all four artifacts exist, delegate to afspec
    - `render(combined)`: check all four artifacts exist, delegate to afspec
    - _Requirements: 02-REQ-4.4, 02-REQ-4.E1, 02-REQ-4.E2, 02-REQ-6.1, 02-REQ-6.2, 02-REQ-6.3, 02-REQ-6.E1_

  - [ ] 4.5 Implement session properties
    - `state` -> SessionState
    - `spec_dir` -> Path
    - `assessment` -> Assessment | None (from assessment_history)
    - _Requirements: 02-REQ-4.1_

  - [ ] 4.V Verify task group 4
    - [ ] Session tests pass: `uv run pytest -q tests/test_session.py`
    - [ ] Session edge case tests pass (TS-02-E7 through TS-02-E11)
    - [ ] Session property tests pass (TS-02-P1, TS-02-P2, TS-02-P5, TS-02-P6)
    - [ ] All existing tests still pass: `uv run pytest -q`
    - [ ] No linter warnings introduced: `uv run ruff check && uv run mypy speclib/`

- [ ] 5. Wiring verification

  - [ ] 5.1 Trace every execution path from design.md end-to-end
    - Path 1: `Campaign.create` -> validate path -> create dir -> write YAML -> return Campaign
    - Path 2: `Campaign.open` -> check YAML -> parse -> return Campaign; `specs()` -> scan -> sort -> return
    - Path 3: `campaign.new_spec` -> validate name -> compute prefix -> create dir -> write prd.md -> write _session.json -> return SpecSession
    - Path 4: SpecSession `init -> assessing -> refining -> prd_accepted -> generating -> generated` (stubs raise NotImplementedError after state check)
    - Path 5: `SpecSession.resume` -> read _session.json -> deserialize -> return SpecSession
    - Path 6: `session.validate` -> check artifacts -> afspec.load_spec -> afspec.validate -> return ValidationResult
    - Verify each function in the chain is actually called by the previous one
    - _Requirements: all_

  - [ ] 5.2 Verify return values propagate correctly
    - `Campaign.create()` returns Campaign consumed by callers
    - `campaign.new_spec()` returns SpecSession consumed by callers
    - `session.validate()` returns ValidationResult
    - `session.render()` returns str or dict
    - _Requirements: all_

  - [ ] 5.3 Run the integration smoke tests
    - All TS-02-SMOKE-* tests pass with real components
    - _Test Spec: TS-02-SMOKE-1 through TS-02-SMOKE-5_

  - [ ] 5.4 Stub / dead-code audit
    - Search speclib/campaign.py and speclib/session.py for `return []`, `return None` on non-Optional returns, `pass`, `# TODO`, `NotImplementedError`
    - Each hit must be justified or replaced
    - `assess()`, `refine()`, `generate()` raising NotImplementedError is expected and documented — note as intentional (spec 03 provides implementation)

  - [ ] 5.5 Cross-spec entry point verification
    - Verify `Campaign` and `SpecSession` are importable from `speclib`
    - Verify `CampaignError` and `SessionError` are importable from `speclib.errors`
    - Verify `CampaignMetadata`, `SessionState`, `Assessment`, `Question`, `ValidationResult`, `GenerateResult`, `RepairSuggestion` are importable
    - Confirm spec 03 can subclass or wrap `assess()` and `generate()` — verify method signatures match the interface in design.md

  - [ ] 5.V Verify wiring group
    - [ ] All smoke tests pass: `uv run pytest -q tests/ -k smoke`
    - [ ] No unjustified stubs remain in speclib/campaign.py or speclib/session.py
    - [ ] All execution paths from design.md are live
    - [ ] All existing tests still pass: `uv run pytest -q`

## Traceability

| Requirement | Test Spec Entry | Implemented By Task | Verified By Test |
|-------------|-----------------|---------------------|------------------|
| 02-REQ-1.1 | TS-02-1 | 3.1 | tests/test_campaign.py::test_campaign_create |
| 02-REQ-1.2 | TS-02-2 | 3.1 | tests/test_campaign.py::test_campaign_create_fails_existing |
| 02-REQ-1.3 | TS-02-3 | 2.3, 3.1 | tests/test_campaign.py::test_campaign_yaml_fields |
| 02-REQ-2.1 | TS-02-4 | 3.2 | tests/test_campaign.py::test_campaign_open |
| 02-REQ-2.2 | TS-02-5 | 3.3 | tests/test_campaign.py::test_campaign_specs_sorted |
| 02-REQ-3.1 | TS-02-6 | 3.4 | tests/test_campaign.py::test_new_spec_string_prd |
| 02-REQ-3.2 | TS-02-7 | 3.4 | tests/test_campaign.py::test_new_spec_path_prd |
| 02-REQ-3.3 | TS-02-8 | 3.4 | tests/test_campaign.py::test_spec_dir_sequential_prefixes |
| 02-REQ-3.4 | TS-02-9 | 3.4 | tests/test_campaign.py::test_prd_frontmatter |
| 02-REQ-4.1 | TS-02-10 | 2.2 | tests/test_session.py::test_session_state_enum |
| 02-REQ-4.2 | TS-02-11 | 4.1 | tests/test_session.py::test_legal_state_transitions |
| 02-REQ-4.3 | TS-02-12 | 4.1 | tests/test_session.py::test_illegal_transition_error_message |
| 02-REQ-4.4 | TS-02-13 | 4.4 | tests/test_session.py::test_accept_prd_from_assessing_and_refining |
| 02-REQ-5.1 | TS-02-14 | 4.2 | tests/test_session.py::test_state_persisted_on_transition |
| 02-REQ-5.2 | TS-02-15 | 4.3 | tests/test_session.py::test_session_resume |
| 02-REQ-5.3 | TS-02-16 | 4.2 | tests/test_session.py::test_session_json_fields |
| 02-REQ-6.1 | TS-02-17 | 4.4 | tests/test_session.py::test_validate_with_artifacts |
| 02-REQ-6.2 | TS-02-18 | 4.4 | tests/test_session.py::test_render_combined |
| 02-REQ-6.3 | TS-02-19 | 4.4 | tests/test_session.py::test_render_individual |
| 02-REQ-1.E1 | TS-02-E1 | 3.1 | tests/test_campaign.py::test_create_non_empty_non_campaign |
| 02-REQ-1.E2 | TS-02-E2 | 3.1 | tests/test_campaign.py::test_create_parent_missing |
| 02-REQ-2.E1 | TS-02-E3 | 3.2 | tests/test_campaign.py::test_open_no_campaign_yaml |
| 02-REQ-2.E2 | TS-02-E4 | 3.2 | tests/test_campaign.py::test_open_invalid_yaml |
| 02-REQ-3.E1 | TS-02-E5 | 3.4 | tests/test_campaign.py::test_new_spec_invalid_name |
| 02-REQ-3.E2 | TS-02-E6 | 3.4 | tests/test_campaign.py::test_new_spec_nonexistent_prd_path |
| 02-REQ-4.E1 | TS-02-E7 | 4.1 | tests/test_session.py::test_generate_from_wrong_state |
| 02-REQ-4.E2 | TS-02-E8 | 4.1 | tests/test_session.py::test_assess_from_generated |
| 02-REQ-5.E1 | TS-02-E9 | 4.3 | tests/test_session.py::test_resume_no_session_json |
| 02-REQ-5.E2 | TS-02-E10 | 4.3 | tests/test_session.py::test_resume_invalid_json |
| 02-REQ-6.E1 | TS-02-E11 | 4.4 | tests/test_session.py::test_validate_render_missing_artifacts |
| Property 1 | TS-02-P1 | 4.1 | tests/test_session.py::test_property_state_machine_total |
| Property 2 | TS-02-P2 | 4.2, 4.3 | tests/test_session.py::test_property_persistence_idempotent |
| Property 3 | TS-02-P3 | 3.4 | tests/test_campaign.py::test_property_numbering_monotonic |
| Property 4 | TS-02-P4 | 3.1 | tests/test_campaign.py::test_property_create_atomic |
| Property 5 | TS-02-P5 | 4.4 | tests/test_session.py::test_property_artifacts_required |
| Property 6 | TS-02-P6 | 4.4 | tests/test_session.py::test_property_accept_prd_states |
| Path 1+3 | TS-02-SMOKE-1 | 3.1, 3.4 | tests/test_campaign.py::test_smoke_campaign_to_spec_creation |
| Path 2 | TS-02-SMOKE-2 | 3.2, 3.3 | tests/test_campaign.py::test_smoke_open_and_list_specs |
| Path 4 | TS-02-SMOKE-3 | 4.1, 4.4 | tests/test_session.py::test_smoke_session_lifecycle |
| Path 5 | TS-02-SMOKE-4 | 4.3 | tests/test_session.py::test_smoke_session_resume |
| Path 6 | TS-02-SMOKE-5 | 4.4 | tests/test_session.py::test_smoke_validate_and_render |
