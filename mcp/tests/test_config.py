"""Tests for env-driven configuration."""

from __future__ import annotations

import pytest

from zebu_mcp.config import ConfigError, ZebuMcpConfig


class TestZebuMcpConfigFromEnv:
    """Behaviour of ``ZebuMcpConfig.from_env``."""

    def test_reads_required_vars(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """Happy path: both required vars set → frozen config returned."""
        monkeypatch.setenv("ZEBU_API_BASE_URL", "https://zebutrader.com")
        monkeypatch.setenv("ZEBU_API_KEY", "zk_abc")
        monkeypatch.delenv("ZEBU_API_TIMEOUT_SECS", raising=False)

        cfg = ZebuMcpConfig.from_env()

        assert cfg.api_base_url == "https://zebutrader.com"
        assert cfg.api_key == "zk_abc"
        assert cfg.timeout_secs == 30.0

    def test_strips_trailing_slash_and_api_v1_prefix(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Users sometimes paste the full ``/api/v1`` URL; strip it."""
        monkeypatch.setenv("ZEBU_API_BASE_URL", "https://zebutrader.com/api/v1/")
        monkeypatch.setenv("ZEBU_API_KEY", "zk_abc")

        cfg = ZebuMcpConfig.from_env()

        assert cfg.api_base_url == "https://zebutrader.com"

    def test_missing_base_url_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing required ZEBU_API_BASE_URL surfaces a config error."""
        monkeypatch.delenv("ZEBU_API_BASE_URL", raising=False)
        monkeypatch.setenv("ZEBU_API_KEY", "zk_abc")

        with pytest.raises(ConfigError, match="ZEBU_API_BASE_URL"):
            ZebuMcpConfig.from_env()

    def test_missing_api_key_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Missing required ZEBU_API_KEY surfaces a config error."""
        monkeypatch.setenv("ZEBU_API_BASE_URL", "https://zebutrader.com")
        monkeypatch.delenv("ZEBU_API_KEY", raising=False)

        with pytest.raises(ConfigError, match="ZEBU_API_KEY"):
            ZebuMcpConfig.from_env()

    def test_invalid_timeout_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Non-numeric timeout is a config error, not a silent fallback."""
        monkeypatch.setenv("ZEBU_API_BASE_URL", "https://zebutrader.com")
        monkeypatch.setenv("ZEBU_API_KEY", "zk_abc")
        monkeypatch.setenv("ZEBU_API_TIMEOUT_SECS", "abc")

        with pytest.raises(ConfigError, match="ZEBU_API_TIMEOUT_SECS"):
            ZebuMcpConfig.from_env()

    def test_non_positive_timeout_raises(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Zero / negative timeout is a config error."""
        monkeypatch.setenv("ZEBU_API_BASE_URL", "https://zebutrader.com")
        monkeypatch.setenv("ZEBU_API_KEY", "zk_abc")
        monkeypatch.setenv("ZEBU_API_TIMEOUT_SECS", "0")

        with pytest.raises(ConfigError, match="> 0"):
            ZebuMcpConfig.from_env()
