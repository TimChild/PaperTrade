"""GetPortfolioBalances query - Calculate balances for multiple portfolios in batch."""

import asyncio
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from zebu.application.exceptions import (
    MarketDataUnavailableError,
    PartialPricingReason,
    TickerNotFoundError,
)
from zebu.application.ports.market_data_port import MarketDataPort
from zebu.application.ports.portfolio_repository import PortfolioRepository
from zebu.application.ports.transaction_repository import TransactionRepository
from zebu.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceResult,
    get_previous_trading_day,
)
from zebu.domain.services.portfolio_calculator import PortfolioCalculator
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.ticker import Ticker

logger = logging.getLogger(__name__)


# Pricing status discriminator for a per-portfolio entry in
# :class:`GetPortfolioBalancesResult`. ``ok`` means every required price
# was fetched successfully; ``loading`` means at least one required
# ticker's current (or previous-close) price could not be resolved and
# the caller should show a "fetching" affordance.
PricingStatus = Literal["ok", "loading"]


@dataclass(frozen=True)
class GetPortfolioBalancesQuery:
    """Input data for retrieving balances for multiple portfolios.

    Attributes:
        portfolio_ids: List of portfolio IDs to calculate balances for
        as_of: Optional reference time for calculation (defaults to now)
    """

    portfolio_ids: list[UUID]
    as_of: datetime | None = None


@dataclass(frozen=True)
class PortfolioBalanceEntry:
    """Per-portfolio entry in a batch balance result.

    Either carries a successful :class:`GetPortfolioBalanceResult` (when
    ``pricing_status == "ok"``) or a structured loading envelope that
    enumerates the tickers whose price could not be resolved (when
    ``pricing_status == "loading"``).

    Cash balance is always populated — it's computed from transactions
    only and does not depend on any market data. The UI can render the
    cash row even on a loading entry; only the market-data-dependent
    rows (holdings value, total, day change) get the skeleton treatment.

    Phase J / Task #214: replaces the prior "always-return-a-result"
    behaviour where missing prices silently dropped tickers from the
    holdings-value sum.
    """

    portfolio_id: UUID
    pricing_status: PricingStatus
    balance: GetPortfolioBalanceResult | None
    cash_balance: Money
    as_of: datetime
    missing_tickers: list[Ticker]
    failed_reason: dict[Ticker, PartialPricingReason]
    retry_after_seconds: int


@dataclass(frozen=True)
class GetPortfolioBalancesResult:
    """Result of retrieving balances for multiple portfolios.

    Attributes:
        entries: Per-portfolio entries in the same order as the input
            ``portfolio_ids``. Each entry carries a ``pricing_status`` of
            ``ok`` (with ``balance`` populated) or ``loading`` (with
            ``missing_tickers`` populated and ``balance == None``).
    """

    entries: list[PortfolioBalanceEntry]

    @property
    def balances(self) -> list[GetPortfolioBalanceResult]:
        """Successful balances only, preserving input order.

        Retained for backwards compatibility with callers that only need
        the OK entries. Callers that must distinguish loading from OK
        should iterate :attr:`entries` directly.
        """
        return [e.balance for e in self.entries if e.balance is not None]


# Default Retry-After window (seconds). Conservative — most prices come
# back from cache in <1s; the AV API path is 1-3s.
_DEFAULT_RETRY_AFTER_SECONDS = 5


class GetPortfolioBalancesHandler:
    """Handler for GetPortfolioBalances batch query.

    Calculates current cash balance and holdings value for multiple portfolios
    using a single database query and batched market data fetches. This
    eliminates the N+1 query problem when loading a dashboard of portfolios.

    Phase J / Task #214 — per-portfolio pricing gating. A portfolio whose
    holdings include a ticker with an unresolved current (or previous-close)
    price is returned with ``pricing_status == "loading"`` and no balance
    figures; portfolios whose required prices are all present render
    normally. A portfolio with no holdings is always ``ok`` (it doesn't
    depend on any price).
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        transaction_repository: TransactionRepository,
        market_data: MarketDataPort,
    ) -> None:
        """Initialize handler with repository dependencies.

        Args:
            portfolio_repository: Repository for portfolio persistence
            transaction_repository: Repository for transaction persistence
            market_data: Market data port for fetching current prices
        """
        self._portfolio_repository = portfolio_repository
        self._transaction_repository = transaction_repository
        self._market_data = market_data

    async def execute(
        self, query: GetPortfolioBalancesQuery
    ) -> GetPortfolioBalancesResult:
        """Execute the GetPortfolioBalances batch query.

        Fetches all transactions in one query, collects unique tickers, then
        fetches current and previous prices in parallel across all portfolios.

        Args:
            query: Query with list of portfolio_ids

        Returns:
            Result containing one entry per portfolio (same order as the
            input). Each entry is either ``pricing_status == "ok"`` with a
            populated :class:`GetPortfolioBalanceResult`, or
            ``pricing_status == "loading"`` with the list of unresolved
            tickers + a ``retry_after_seconds`` hint.
        """
        if not query.portfolio_ids:
            return GetPortfolioBalancesResult(entries=[])

        current_time = query.as_of or datetime.now(UTC)

        # Fetch all transactions for all portfolios in ONE query
        transactions_by_portfolio = (
            await self._transaction_repository.get_by_portfolios(query.portfolio_ids)
        )

        # Calculate holdings for each portfolio
        holdings_by_portfolio = {}
        all_tickers: set[Ticker] = set()

        for portfolio_id in query.portfolio_ids:
            transactions = transactions_by_portfolio.get(portfolio_id, [])
            holdings = PortfolioCalculator.calculate_holdings(transactions)
            holdings_by_portfolio[portfolio_id] = holdings
            for holding in holdings:
                all_tickers.add(holding.ticker)

        # Fetch all unique current + previous prices in parallel. We
        # record per-ticker success/failure (instead of silently
        # dropping failures into a partial dict) so per-portfolio
        # gating can decide which portfolios to mark "loading".
        current_prices_dict: dict[Ticker, Money] = {}
        current_failed_reason: dict[Ticker, PartialPricingReason] = {}
        previous_prices_dict: dict[Ticker, Money] = {}
        previous_failed_reason: dict[Ticker, PartialPricingReason] = {}

        previous_date = get_previous_trading_day(current_time)

        if all_tickers:

            async def fetch_current_price(
                ticker: Ticker,
            ) -> tuple[Ticker, Money | None, PartialPricingReason | None]:
                """Fetch current price; on error return the typed reason."""
                try:
                    price_point = await self._market_data.get_current_price(ticker)
                    return ticker, price_point.price, None
                except TickerNotFoundError as e:
                    logger.warning(
                        f"Failed to fetch current price for {ticker.symbol}: {e}"
                    )
                    return ticker, None, "ticker_not_found"
                except MarketDataUnavailableError as e:
                    logger.warning(
                        f"Failed to fetch current price for {ticker.symbol}: {e}"
                    )
                    return ticker, None, "market_data_unavailable"

            async def fetch_previous_price(
                ticker: Ticker,
            ) -> tuple[Ticker, Money | None, PartialPricingReason | None]:
                """Fetch previous-close price; on error return the typed reason."""
                try:
                    price_point = await self._market_data.get_price_at(
                        ticker, previous_date
                    )
                    return ticker, price_point.price, None
                except TickerNotFoundError as e:
                    logger.warning(
                        f"Failed to fetch previous close price for {ticker.symbol}: {e}"
                    )
                    return ticker, None, "ticker_not_found"
                except MarketDataUnavailableError as e:
                    logger.warning(
                        f"Failed to fetch previous close price for {ticker.symbol}: {e}"
                    )
                    return ticker, None, "market_data_unavailable"

            current_results = await asyncio.gather(
                *[fetch_current_price(t) for t in all_tickers]
            )
            for ticker, price, reason in current_results:
                if price is not None:
                    current_prices_dict[ticker] = price
                elif reason is not None:
                    current_failed_reason[ticker] = reason

            previous_results = await asyncio.gather(
                *[fetch_previous_price(t) for t in all_tickers]
            )
            for ticker, price, reason in previous_results:
                if price is not None:
                    previous_prices_dict[ticker] = price
                elif reason is not None:
                    previous_failed_reason[ticker] = reason

        # Compute per-portfolio entry. A portfolio is "loading" when any
        # of its held tickers lacks a current OR previous-close price.
        entries: list[PortfolioBalanceEntry] = []
        for portfolio_id in query.portfolio_ids:
            transactions = transactions_by_portfolio.get(portfolio_id, [])
            cash_balance = PortfolioCalculator.calculate_cash_balance(transactions)
            holdings = holdings_by_portfolio[portfolio_id]

            if not holdings:
                # Cash-only portfolios are unaffected by pricing failures.
                entries.append(
                    PortfolioBalanceEntry(
                        portfolio_id=portfolio_id,
                        pricing_status="ok",
                        balance=GetPortfolioBalanceResult(
                            portfolio_id=portfolio_id,
                            cash_balance=cash_balance,
                            holdings_value=Money(
                                Decimal("0.00"), cash_balance.currency
                            ),
                            total_value=cash_balance,
                            currency=cash_balance.currency,
                            as_of=current_time,
                            daily_change=Money(Decimal("0.00"), cash_balance.currency),
                            daily_change_percent=Decimal("0.00"),
                        ),
                        cash_balance=cash_balance,
                        as_of=current_time,
                        missing_tickers=[],
                        failed_reason={},
                        retry_after_seconds=_DEFAULT_RETRY_AFTER_SECONDS,
                    )
                )
                continue

            # Gating: enumerate this portfolio's tickers and check both
            # the current and previous-close price maps. A ticker is
            # "missing" if EITHER price fetch failed — the daily-change
            # calculation needs both. Order is stable (input order of
            # holdings) so the loading UI can render the same list across
            # re-fetches.
            missing_tickers: list[Ticker] = []
            failed_reason: dict[Ticker, PartialPricingReason] = {}
            seen: set[Ticker] = set()
            for holding in holdings:
                ticker = holding.ticker
                if ticker in seen:
                    continue
                seen.add(ticker)
                if ticker not in current_prices_dict:
                    missing_tickers.append(ticker)
                    failed_reason[ticker] = current_failed_reason.get(
                        ticker, "market_data_unavailable"
                    )
                elif ticker not in previous_prices_dict:
                    missing_tickers.append(ticker)
                    failed_reason[ticker] = previous_failed_reason.get(
                        ticker, "market_data_unavailable"
                    )

            if missing_tickers:
                entries.append(
                    PortfolioBalanceEntry(
                        portfolio_id=portfolio_id,
                        pricing_status="loading",
                        balance=None,
                        cash_balance=cash_balance,
                        as_of=current_time,
                        missing_tickers=missing_tickers,
                        failed_reason=failed_reason,
                        retry_after_seconds=_DEFAULT_RETRY_AFTER_SECONDS,
                    )
                )
                continue

            holdings_value = PortfolioCalculator.calculate_portfolio_value(
                holdings, current_prices_dict
            )
            total_value = PortfolioCalculator.calculate_total_value(
                cash_balance, holdings_value
            )
            daily_change, daily_change_percent = (
                PortfolioCalculator.calculate_daily_change(
                    holdings, current_prices_dict, previous_prices_dict
                )
            )

            entries.append(
                PortfolioBalanceEntry(
                    portfolio_id=portfolio_id,
                    pricing_status="ok",
                    balance=GetPortfolioBalanceResult(
                        portfolio_id=portfolio_id,
                        cash_balance=cash_balance,
                        holdings_value=holdings_value,
                        total_value=total_value,
                        currency=cash_balance.currency,
                        as_of=current_time,
                        daily_change=daily_change,
                        daily_change_percent=daily_change_percent,
                    ),
                    cash_balance=cash_balance,
                    as_of=current_time,
                    missing_tickers=[],
                    failed_reason={},
                    retry_after_seconds=_DEFAULT_RETRY_AFTER_SECONDS,
                )
            )

        return GetPortfolioBalancesResult(entries=entries)
