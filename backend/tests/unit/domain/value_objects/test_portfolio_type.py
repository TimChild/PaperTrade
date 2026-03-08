"""Tests for PortfolioType value object."""

from zebu.domain.value_objects.portfolio_type import PortfolioType


class TestPortfolioType:
    """Tests for PortfolioType enum."""

    def test_paper_trading_value(self) -> None:
        """PAPER_TRADING should have the expected string value."""
        assert PortfolioType.PAPER_TRADING.value == "PAPER_TRADING"

    def test_backtest_value(self) -> None:
        """BACKTEST should have the expected string value."""
        assert PortfolioType.BACKTEST.value == "BACKTEST"

    def test_all_members_present(self) -> None:
        """Enum should contain exactly the expected members."""
        assert set(PortfolioType) == {
            PortfolioType.PAPER_TRADING,
            PortfolioType.BACKTEST,
        }

    def test_from_string_round_trip(self) -> None:
        """Should reconstruct enum from its string value."""
        assert PortfolioType("PAPER_TRADING") == PortfolioType.PAPER_TRADING
        assert PortfolioType("BACKTEST") == PortfolioType.BACKTEST
