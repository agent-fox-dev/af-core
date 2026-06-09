"""Tests for spec authoring session state machine and persistence.

Test Spec Entries: TS-02-10 through TS-02-19 (acceptance criteria),
TS-02-E7 through TS-02-E11 (edge cases).
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from speclib.campaign import Campaign

from speclib.errors import SessionError
from speclib.session import (
    SessionState,
    SpecSession,
    ValidationResult,
)

# ---------------------------------------------------------------------------
# Helper: create a session in a specific state for testing
# ---------------------------------------------------------------------------

def _create_session(tmp_path: Path, state: SessionState | None = None) -> SpecSession:
    """Create a SpecSession in a spec directory, optionally in a given state.

    Uses Campaign.new_spec to create the session in init state, then
    directly writes the desired state to _session.json for test setup.
    """
    camp_dir = tmp_path / "camp"
    if not (camp_dir / "campaign.yaml").exists():
        Campaign.create(camp_dir, "Test", "Desc")
    camp = Campaign.open(camp_dir)

    # Create a new spec each call (unique name from state)
    spec_name = f"s_{state.value if state else 'init'}".replace(" ", "_")
    session = camp.new_spec(spec_name, "PRD content")

    if state is not None and state != SessionState.INIT:
        # Directly set state in _session.json for test precondition setup
        session_file = session.spec_dir / "_session.json"
        data = json.loads(session_file.read_text())
        data["state"] = state.value
        session_file.write_text(json.dumps(data))
        # Resume to get a session in the desired state
        session = SpecSession.resume(session.spec_dir)

    return session


def _create_session_with_all_artifacts(tmp_path: Path) -> SpecSession:
    """Create a SpecSession whose spec dir has all four required artifacts."""
    camp_dir = tmp_path / "camp_artifacts"
    if not (camp_dir / "campaign.yaml").exists():
        Campaign.create(camp_dir, "Test", "Desc")
    camp = Campaign.open(camp_dir)
    session = camp.new_spec("full_spec", "# PRD\n\nContent")

    # Create the four required artifacts
    spec_dir = session.spec_dir
    for artifact in ["requirements.md", "design.md", "test_spec.md"]:
        (spec_dir / artifact).write_text(f"# {artifact}\n\nPlaceholder content")

    return session


# ---------------------------------------------------------------------------
# Acceptance criterion tests: TS-02-10 through TS-02-19
# ---------------------------------------------------------------------------


class TestSessionStateEnum:
    """Tests for SessionState enum — TS-02-10."""

    def test_ts02_10_session_state_enum_values(self) -> None:
        """TS-02-10: SessionState enum has all six required values.

        Requirement: 02-REQ-4.1
        """
        assert SessionState.INIT.value == "init"
        assert SessionState.ASSESSING.value == "assessing"
        assert SessionState.REFINING.value == "refining"
        assert SessionState.PRD_ACCEPTED.value == "prd_accepted"
        assert SessionState.GENERATING.value == "generating"
        assert SessionState.GENERATED.value == "generated"
        assert len(SessionState) == 6


class TestStateTransitions:
    """Tests for session state machine transitions — TS-02-11 through TS-02-13."""

    def test_ts02_11_legal_state_transitions(self, tmp_path: Path) -> None:
        """TS-02-11: Legal transitions succeed, illegal transitions raise SessionError.

        Requirement: 02-REQ-4.2

        Legal transitions (from design.md):
          init -> assessing (assess)
          assessing -> refining (refine)
          assessing -> prd_accepted (accept_prd)
          refining -> assessing (assess)
          refining -> prd_accepted (accept_prd)
          prd_accepted -> generating (generate)

        Stub methods (assess, refine, generate) should check state BEFORE
        raising NotImplementedError — so illegal state raises SessionError,
        while legal state raises NotImplementedError.
        """
        # Legal: init -> assessing via assess()
        session = _create_session(tmp_path, SessionState.INIT)
        # assess() should pass state check then raise NotImplementedError (stub)
        with pytest.raises(NotImplementedError):
            session.assess()

        # Illegal: init -> refining via refine()
        session = _create_session(tmp_path, SessionState.INIT)
        with pytest.raises(SessionError):
            session.refine({})

        # Illegal: init -> generating via generate()
        session = _create_session(tmp_path, SessionState.INIT)
        with pytest.raises(SessionError):
            session.generate()

        # Legal: assessing -> refining via refine()
        session = _create_session(tmp_path, SessionState.ASSESSING)
        with pytest.raises(NotImplementedError):
            session.refine({})

        # Legal: assessing -> prd_accepted via accept_prd()
        session = _create_session(tmp_path, SessionState.ASSESSING)
        session.accept_prd()
        assert session.state == SessionState.PRD_ACCEPTED

        # Legal: refining -> assessing via assess()
        session = _create_session(tmp_path, SessionState.REFINING)
        with pytest.raises(NotImplementedError):
            session.assess()

        # Legal: refining -> prd_accepted via accept_prd()
        session = _create_session(tmp_path, SessionState.REFINING)
        session.accept_prd()
        assert session.state == SessionState.PRD_ACCEPTED

        # Legal: prd_accepted -> generating via generate()
        session = _create_session(tmp_path, SessionState.PRD_ACCEPTED)
        with pytest.raises(NotImplementedError):
            session.generate()

        # Illegal: prd_accepted -> assess()
        session = _create_session(tmp_path, SessionState.PRD_ACCEPTED)
        with pytest.raises(SessionError):
            session.assess()

    def test_ts02_12_illegal_transition_error_message(self, tmp_path: Path) -> None:
        """TS-02-12: SessionError names current state and required state.

        Requirement: 02-REQ-4.3
        """
        session = _create_session(tmp_path, SessionState.INIT)
        with pytest.raises(SessionError) as exc_info:
            session.generate()

        error_msg = str(exc_info.value)
        assert "init" in error_msg
        assert "prd_accepted" in error_msg

    def test_ts02_13_accept_prd_from_assessing_and_refining(
        self, tmp_path: Path
    ) -> None:
        """TS-02-13: accept_prd() works from both assessing and refining states.

        Requirement: 02-REQ-4.4
        """
        session_a = _create_session(tmp_path, SessionState.ASSESSING)
        session_a.accept_prd()
        assert session_a.state == SessionState.PRD_ACCEPTED

        session_r = _create_session(tmp_path, SessionState.REFINING)
        session_r.accept_prd()
        assert session_r.state == SessionState.PRD_ACCEPTED


class TestSessionPersistence:
    """Tests for session persistence — TS-02-14 through TS-02-16."""

    def test_ts02_14_state_persisted_on_transition(self, tmp_path: Path) -> None:
        """TS-02-14: _session.json is updated on every state transition.

        Requirement: 02-REQ-5.1
        """
        session = _create_session(tmp_path, SessionState.ASSESSING)
        session.accept_prd()

        data = json.loads((session.spec_dir / "_session.json").read_text())
        assert data["state"] == "prd_accepted"

    def test_ts02_15_session_resume(self, tmp_path: Path) -> None:
        """TS-02-15: SpecSession.resume restores session state from _session.json.

        Requirement: 02-REQ-5.2
        """
        session = _create_session(tmp_path, SessionState.ASSESSING)
        session.accept_prd()

        resumed = SpecSession.resume(session.spec_dir)
        assert resumed.state == SessionState.PRD_ACCEPTED
        assert resumed.spec_dir == session.spec_dir

    def test_ts02_16_session_json_fields(self, tmp_path: Path) -> None:
        """TS-02-16: _session.json contains all required fields.

        Requirement: 02-REQ-5.3
        """
        camp_dir = tmp_path / "json_fields"
        camp = Campaign.create(camp_dir, "Test", "Desc")
        session = camp.new_spec("test_spec", "PRD content")

        data = json.loads((session.spec_dir / "_session.json").read_text())
        assert "state" in data
        assert "prd_path" in data
        assert "assessment_history" in data
        assert "qa_exchanges" in data
        assert "generated_artifacts" in data
        assert "mode" in data


class TestSessionValidateRender:
    """Tests for validate() and render() — TS-02-17 through TS-02-19."""

    def test_ts02_17_validate_with_artifacts(self, tmp_path: Path) -> None:
        """TS-02-17: validate() loads spec via afspec and returns ValidationResult.

        Requirement: 02-REQ-6.1
        """
        session = _create_session_with_all_artifacts(tmp_path)

        # Mock afspec at the boundary
        mock_spec = MagicMock()
        mock_validation = ValidationResult(
            valid=True,
            schema_errors=[],
            integrity_errors=[],
            repair_suggestions=[],
        )

        with (
            patch("speclib.session.afspec") as mock_afspec,
        ):
            mock_afspec.load_spec.return_value = mock_spec
            mock_afspec.validate.return_value = mock_validation

            result = session.validate()

        assert isinstance(result, ValidationResult)
        assert isinstance(result.valid, bool)
        assert isinstance(result.schema_errors, list)
        assert isinstance(result.integrity_errors, list)

    def test_ts02_18_render_combined(self, tmp_path: Path) -> None:
        """TS-02-18: render(combined=True) returns a single markdown string.

        Requirement: 02-REQ-6.2
        """
        session = _create_session_with_all_artifacts(tmp_path)

        mock_spec = MagicMock()

        with patch("speclib.session.afspec") as mock_afspec:
            mock_afspec.load_spec.return_value = mock_spec
            mock_afspec.render_combined.return_value = "# Combined"

            result = session.render(combined=True)

        assert isinstance(result, str)
        assert len(result) > 0

    def test_ts02_19_render_individual(self, tmp_path: Path) -> None:
        """TS-02-19: render(combined=False) returns artifact name dict.

        Requirement: 02-REQ-6.3
        """
        session = _create_session_with_all_artifacts(tmp_path)

        mock_spec = MagicMock()

        with patch("speclib.session.afspec") as mock_afspec:
            mock_afspec.load_spec.return_value = mock_spec
            mock_afspec.render_individual.return_value = {"prd": "# PRD content"}

            result = session.render(combined=False)

        assert isinstance(result, dict)
        assert all(
            isinstance(k, str) and isinstance(v, str)
            for k, v in result.items()
        )


# ---------------------------------------------------------------------------
# Edge case tests: TS-02-E7 through TS-02-E11
# ---------------------------------------------------------------------------


class TestSessionEdgeCases:
    """Edge case tests for session operations — TS-02-E7 through TS-02-E11."""

    def test_ts02_e7_generate_from_wrong_state(self, tmp_path: Path) -> None:
        """TS-02-E7: SessionError when generate() called from non-prd_accepted state.

        Requirement: 02-REQ-4.E1
        """
        session_init = _create_session(tmp_path, SessionState.INIT)
        with pytest.raises(SessionError):
            session_init.generate()

        session_assessing = _create_session(tmp_path, SessionState.ASSESSING)
        with pytest.raises(SessionError):
            session_assessing.generate()

    def test_ts02_e8_assess_from_generated(self, tmp_path: Path) -> None:
        """TS-02-E8: SessionError when assess() called from generated terminal state.

        Requirement: 02-REQ-4.E2
        """
        session = _create_session(tmp_path, SessionState.GENERATED)
        with pytest.raises(SessionError):
            session.assess()

    def test_ts02_e9_resume_no_session_json(self, tmp_path: Path) -> None:
        """TS-02-E9: SessionError when resume() called without _session.json.

        Requirement: 02-REQ-5.E1
        """
        empty_dir = tmp_path / "no_session"
        empty_dir.mkdir()

        with pytest.raises(SessionError):
            SpecSession.resume(empty_dir)

    def test_ts02_e10_resume_invalid_json(self, tmp_path: Path) -> None:
        """TS-02-E10: SessionError when _session.json contains invalid JSON.

        Requirement: 02-REQ-5.E2
        """
        bad_dir = tmp_path / "bad_json"
        bad_dir.mkdir()
        (bad_dir / "_session.json").write_text("{invalid json!!!")

        with pytest.raises(SessionError):
            SpecSession.resume(bad_dir)

    def test_ts02_e11_validate_render_missing_artifacts(
        self, tmp_path: Path
    ) -> None:
        """TS-02-E11: SessionError when validate/render called with missing artifacts.

        Requirement: 02-REQ-6.E1
        """
        # Session with only prd.md — missing requirements.md, design.md, test_spec.md
        camp_dir = tmp_path / "missing_artifacts"
        camp = Campaign.create(camp_dir, "Test", "Desc")
        session = camp.new_spec("incomplete", "PRD content")

        with pytest.raises(SessionError) as exc_info:
            session.validate()
        error_msg = str(exc_info.value)
        assert "requirements.md" in error_msg
        assert "design.md" in error_msg
        assert "test_spec.md" in error_msg

        with pytest.raises(SessionError) as exc_info:
            session.render()
        error_msg = str(exc_info.value)
        assert "requirements.md" in error_msg
