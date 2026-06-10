"""Tests for Anthropic client factory.

Test Spec Entries: TS-01-11 through TS-01-15, TS-01-E4 through TS-01-E6,
TS-01-P3, TS-01-SMOKE-2.

Note: Auth client tests mock the anthropic SDK constructors to avoid real
API calls. The mock targets assume speclib.auth uses ``import anthropic``
style imports (async variants: AsyncAnthropic, AsyncAnthropicBedrock,
AsyncAnthropicVertex).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest


class TestClientFactory:
    """Tests for create_client function."""

    def test_ts01_11_api_key_client(
        self,
        clean_env: None,
        mock_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-11: API key auth creates Anthropic client.

        Requirement: 01-REQ-3.1
        When ANTHROPIC_API_KEY is set and AF_SPEC_AUTH is not set or is
        'api_key', the client factory returns an Anthropic instance.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from speclib.auth import create_client

        with patch("speclib.auth.anthropic.AsyncAnthropic") as mock_cls:
            client, model = create_client()
            mock_cls.assert_called_once()
            assert client is mock_cls.return_value
            assert model == "claude-sonnet-4-6"

    def test_ts01_12_bedrock_client(
        self,
        clean_env: None,
        mock_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-12: Bedrock auth creates AnthropicBedrock client.

        Requirement: 01-REQ-3.2
        When AF_SPEC_AUTH is 'bedrock', the client factory returns an
        AnthropicBedrock instance.
        """
        monkeypatch.setenv("AF_SPEC_AUTH", "bedrock")
        from speclib.auth import create_client

        with patch("speclib.auth.anthropic.AsyncAnthropicBedrock") as mock_cls:
            client, model = create_client()
            mock_cls.assert_called_once()
            assert client is mock_cls.return_value

    def test_ts01_13_vertex_client(
        self,
        clean_env: None,
        mock_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-13: Vertex auth creates AnthropicVertex client.

        Requirement: 01-REQ-3.3
        When AF_SPEC_AUTH is 'vertex' and required env vars are set,
        the client factory returns an AnthropicVertex instance.
        """
        monkeypatch.setenv("AF_SPEC_AUTH", "vertex")
        monkeypatch.setenv("AF_SPEC_VERTEX_PROJECT", "test-project")
        monkeypatch.setenv("AF_SPEC_VERTEX_REGION", "us-east5")
        from speclib.auth import create_client

        with patch("speclib.auth.anthropic.AsyncAnthropicVertex") as mock_cls:
            client, model = create_client()
            mock_cls.assert_called_once()
            assert client is mock_cls.return_value

    def test_ts01_14_config_fallback(
        self,
        clean_env: None,
        mock_home: Path,
    ) -> None:
        """TS-01-14: create_client uses SpecToolConfig as fallback.

        Requirement: 01-REQ-3.4
        When env vars are not set, create_client falls back to the
        provided SpecToolConfig values.
        """
        from speclib.auth import create_client
        from speclib.config import SpecToolConfig

        config = SpecToolConfig(auth_method="api_key", api_key="test-key")
        with patch("speclib.auth.anthropic.AsyncAnthropic") as mock_cls:
            client, model = create_client(config)
            mock_cls.assert_called_once()
            assert client is mock_cls.return_value

    def test_ts01_15_yaml_auth_method(
        self,
        clean_env: None,
        mock_home: Path,
        settings_yaml: Path,
    ) -> None:
        """TS-01-15: Settings.yaml auth_method used when no AF_SPEC_AUTH.

        Requirement: 01-REQ-3.5

        Extended per skeptic review: also verifies create_client uses the
        YAML-loaded auth_method by asserting the returned client type.
        """
        settings_yaml.write_text(
            "spec_tool:\n  auth:\n    method: bedrock\n"
        )
        from speclib.auth import create_client
        from speclib.config import load_config

        config = load_config()
        assert config.auth_method == "bedrock"

        # Verify create_client actually uses the YAML auth method
        with patch("speclib.auth.anthropic.AsyncAnthropicBedrock") as mock_cls:
            client, _model = create_client(config)
            mock_cls.assert_called_once()
            assert client is mock_cls.return_value


class TestClientEdgeCases:
    """Edge case tests for client factory."""

    def test_ts01_e4_invalid_auth_method(
        self,
        clean_env: None,
        mock_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-E4: ConfigError for unrecognized auth method.

        Requirement: 01-REQ-3.E1
        Error message must list valid methods: api_key, bedrock, vertex.
        """
        monkeypatch.setenv("AF_SPEC_AUTH", "invalid_method")
        from speclib.auth import create_client
        from speclib.errors import ConfigError

        with pytest.raises(ConfigError) as exc_info:
            create_client()
        error_msg = str(exc_info.value)
        assert "api_key" in error_msg
        assert "bedrock" in error_msg
        assert "vertex" in error_msg

    def test_ts01_e5_missing_api_key(
        self,
        clean_env: None,
        mock_home: Path,
    ) -> None:
        """TS-01-E5: ConfigError when api_key auth has no key.

        Requirement: 01-REQ-3.E2

        Note: clean_env fixture ensures ANTHROPIC_API_KEY is unset,
        per skeptic review finding about false negatives in environments
        where ANTHROPIC_API_KEY may be set.
        """
        from speclib.auth import create_client
        from speclib.config import SpecToolConfig
        from speclib.errors import ConfigError

        config = SpecToolConfig(auth_method="api_key", api_key=None)
        with pytest.raises(ConfigError):
            create_client(config)

    def test_ts01_e6_missing_vertex_project(
        self,
        clean_env: None,
        mock_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-E6: ConfigError when vertex auth lacks project.

        Requirement: 01-REQ-3.E3
        AF_SPEC_VERTEX_PROJECT deliberately not set (clean_env removes it).
        """
        monkeypatch.setenv("AF_SPEC_AUTH", "vertex")
        # AF_SPEC_VERTEX_PROJECT is not set — clean_env ensures removal
        from speclib.auth import create_client
        from speclib.errors import ConfigError

        with pytest.raises(ConfigError):
            create_client()


class TestClientProperties:
    """Property-based tests for client factory."""

    @pytest.mark.parametrize(
        ("auth_method", "expected_cls_name"),
        [
            ("api_key", "AsyncAnthropic"),
            ("bedrock", "AsyncAnthropicBedrock"),
            ("vertex", "AsyncAnthropicVertex"),
        ],
    )
    def test_ts01_p3_client_type_matches_auth(
        self,
        auth_method: str,
        expected_cls_name: str,
        clean_env: None,
        mock_home: Path,
    ) -> None:
        """TS-01-P3: Client type matches auth method.

        Property 3 from design.md.
        Validates: 01-REQ-3.1, 01-REQ-3.2, 01-REQ-3.3

        For any valid auth_method, the returned client's type must match
        the expected SDK class.
        """
        from speclib.auth import create_client
        from speclib.config import SpecToolConfig

        config = SpecToolConfig(
            auth_method=auth_method,
            api_key="test-key",
            vertex_project="test-project",
            vertex_region="us-east5",
        )
        with patch(f"speclib.auth.anthropic.{expected_cls_name}") as mock_cls:
            client, _ = create_client(config)
            mock_cls.assert_called_once()
            assert client is mock_cls.return_value


class TestClientSmoke:
    """Integration smoke tests for client creation."""

    def test_ts01_smoke2_client_creation_end_to_end(
        self,
        clean_env: None,
        mock_home: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """TS-01-SMOKE-2: Full path from config load to client creation.

        Execution Path 2 from design.md.
        Must NOT mock create_client or load_config — only the anthropic
        SDK constructor is mocked to avoid real API calls.
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
        from speclib.auth import create_client

        with patch("speclib.auth.anthropic.AsyncAnthropic") as mock_cls:
            client, model = create_client()
            assert client is mock_cls.return_value
            assert model == "claude-sonnet-4-6"
