"""Tests for speclib configuration loading.

Test Spec Entries: TS-01-7 through TS-01-10, TS-01-E1 through TS-01-E3,
TS-01-P1, TS-01-P2, TS-01-SMOKE-1.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from hypothesis import given
from hypothesis import strategies as st


class TestConfigLoading:
    """Tests for load_config and SpecToolConfig."""

    def test_ts01_7_load_from_yaml(
        self,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
    ) -> None:
        """TS-01-7: Config loads from settings.yaml.

        Requirement: 01-REQ-2.1
        Verifies load_config reads the spec_tool section from settings.yaml.
        """
        settings_yaml.write_text("spec_tool:\n  model: claude-opus-4-6\n")
        from speclib.config import load_config

        config = load_config()
        assert config.model == "claude-opus-4-6"

    def test_ts01_8_env_overrides_yaml(
        self,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-8: Environment variables override settings.yaml values.

        Requirement: 01-REQ-2.2
        """
        settings_yaml.write_text("spec_tool:\n  model: claude-opus-4-6\n")
        monkeypatch.setenv("AF_SPEC_MODEL", "claude-haiku-4-5-20251001")
        from speclib.config import load_config

        config = load_config()
        assert config.model == "claude-haiku-4-5-20251001"

    def test_ts01_9_config_fields(self) -> None:
        """TS-01-9: SpecToolConfig has required fields.

        Requirement: 01-REQ-2.3
        SpecToolConfig must have model, auth_method, and api_key attributes.
        """
        from speclib.config import SpecToolConfig

        config = SpecToolConfig()
        assert hasattr(config, "model")
        assert hasattr(config, "auth_method")
        assert hasattr(config, "api_key")

    def test_ts01_10_defaults(
        self,
        clean_env: None,
        mock_home: Path,
    ) -> None:
        """TS-01-10: Default config values when no config file or env vars.

        Requirement: 01-REQ-2.4
        """
        from speclib.config import load_config

        config = load_config()
        assert config.model == "claude-sonnet-4-6"
        assert config.auth_method == "api_key"
        assert config.api_key is None


class TestConfigEdgeCases:
    """Edge case tests for configuration loading."""

    def test_ts01_e1_invalid_yaml(
        self,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
    ) -> None:
        """TS-01-E1: Invalid YAML raises ConfigError with file path.

        Requirement: 01-REQ-2.E1
        """
        settings_yaml.write_text(":::bad yaml")
        from speclib.config import load_config
        from speclib.errors import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            load_config()
        # Error message must include the file path
        assert str(settings_yaml) in str(exc_info.value)

    def test_ts01_e2_missing_section(
        self,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
    ) -> None:
        """TS-01-E2: Missing spec_tool section uses defaults.

        Requirement: 01-REQ-2.E2
        """
        settings_yaml.write_text("other_tool:\n  key: value\n")
        from speclib.config import load_config

        config = load_config()
        assert config.model == "claude-sonnet-4-6"

    def test_ts01_e3_unknown_keys(
        self,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
    ) -> None:
        """TS-01-E3: Unknown keys in spec_tool are silently ignored.

        Requirement: 01-REQ-2.E3
        """
        settings_yaml.write_text(
            "spec_tool:\n  unknown_key: value\n  model: test-model\n"
        )
        from speclib.config import load_config

        config = load_config()
        assert config.model == "test-model"


class TestConfigProperties:
    """Property-based tests for configuration."""

    @given(
        env_model=st.text(
            min_size=1,
            alphabet=st.characters(categories=("L", "N")),
        ),
    )
    def test_ts01_p1_env_always_overrides_yaml(
        self,
        env_model: str,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-P1: Env vars always override YAML values.

        Property 1 from design.md.
        Validates: 01-REQ-2.2

        For any model string set via AF_SPEC_MODEL, the loaded config
        must use it regardless of the YAML value.
        """
        monkeypatch.setenv("AF_SPEC_MODEL", env_model)
        settings_yaml.write_text("spec_tool:\n  model: different-value\n")
        from speclib.config import load_config

        config = load_config()
        assert config.model == env_model

    @given(iteration=st.integers(min_value=0, max_value=10))
    def test_ts01_p2_defaults_consistent(
        self,
        iteration: int,
        clean_env: None,
        mock_home: Path,
    ) -> None:
        """TS-01-P2: Defaults are consistent across invocations.

        Property 2 from design.md.
        Validates: 01-REQ-2.4

        Without any config source, defaults are always the same.
        """
        from speclib.config import load_config

        config = load_config()
        assert config.model == "claude-sonnet-4-6"
        assert config.auth_method == "api_key"


class TestConfigSmoke:
    """Integration smoke tests for configuration."""

    def test_ts01_smoke1_config_load_end_to_end(
        self,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-SMOKE-1: Full config load from YAML + env var override.

        Execution Path 1 from design.md.
        Must NOT mock load_config internals.
        """
        settings_yaml.write_text(
            "spec_tool:\n  model: yaml-model\n  auth:\n    method: api_key\n"
        )
        monkeypatch.setenv("AF_SPEC_MODEL", "env-model")
        from speclib.config import load_config

        config = load_config()
        assert config.model == "env-model"
        assert config.auth_method == "api_key"
