"""BacktestTransactionBuilder - Stateful in-memory portfolio simulator.

Maintains portfolio cash and holdings state during backtest simulation,
creating validated Transaction objects via the trade_factory functions.
"""

import logging
from datetime import datetime
from decimal import ROUND_DOWN, Decimal
from uuid import UUID

from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.exceptions import InsufficientFundsError, InsufficientSharesError
from zebu.domain.services.trade_factory import (
    create_buy_transaction,
    create_sell_transaction,
)
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trade_signal import TradeAction, TradeSignal

logger = logging.getLogger(__name__)


class BacktestTransactionBuilder:
    """In-memory portfolio state tracker that creates validated transactions.

    Maintains in-memory cash balance and holdings during a backtest simulation.
    Applies trade signals by creating Transaction objects through the trade_factory,
    updating state on success and silently skipping invalid signals.

    This is a stateful helper — not a service. It is used exclusively by
    BacktestExecutor during simulation.
    """

    def __init__(self, portfolio_id: UUID, initial_cash: Money) -> None:
        """Initialize builder with a portfolio ID and starting cash.

        Args:
            portfolio_id: The backtest portfolio's ID
            initial_cash: Starting cash balance
        """
        self._portfolio_id = portfolio_id
        self._cash_balance: Money = initial_cash
        self._holdings: dict[str, Quantity] = {}
        self._transactions: list[Transaction] = []

    @property
    def cash_balance(self) -> Money:
        """Current cash balance."""
        return self._cash_balance

    @property
    def holdings(self) -> dict[str, Quantity]:
        """Current holdings by ticker symbol."""
        return dict(self._holdings)

    @property
    def transactions(self) -> list[Transaction]:
        """All created transactions (copy)."""
        return list(self._transactions)

    def apply_signal(
        self,
        signal: TradeSignal,
        price_per_share: Money,
        timestamp: datetime,
    ) -> Transaction | None:
        """Apply a trade signal, creating a transaction if valid.

        For amount-based BUY signals, resolves to whole-share quantity via
        floor(amount / price_per_share). Returns None if the signal cannot
        be executed (insufficient funds/shares, zero quantity after floor, etc).

        Args:
            signal: The trade signal to apply
            price_per_share: Current price per share for the ticker
            timestamp: Timestamp for the created transaction

        Returns:
            Transaction if the signal was executed, None otherwise
        """
        if signal.action == TradeAction.BUY:
            return self._apply_buy(signal, price_per_share, timestamp)
        else:
            return self._apply_sell(signal, price_per_share, timestamp)

    def _apply_buy(
        self,
        signal: TradeSignal,
        price_per_share: Money,
        timestamp: datetime,
    ) -> Transaction | None:
        """Apply a BUY signal."""
        # Resolve quantity from signal
        if signal.amount is not None:
            if price_per_share.amount <= Decimal("0"):
                return None
            raw_qty = signal.amount / price_per_share.amount
            floored = raw_qty.to_integral_value(rounding=ROUND_DOWN)
            if floored <= Decimal("0"):
                logger.debug(
                    f"Skipping BUY {signal.ticker}: "
                    f"amount {signal.amount} too small at price {price_per_share}"
                )
                return None
            quantity = Quantity(floored)
        else:
            # signal.quantity is not None
            assert signal.quantity is not None
            quantity = Quantity(signal.quantity)

        ticker = Ticker(signal.ticker)

        try:
            transaction = create_buy_transaction(
                portfolio_id=self._portfolio_id,
                ticker=ticker,
                quantity=quantity,
                price_per_share=price_per_share,
                cash_balance=self._cash_balance,
                timestamp=timestamp,
            )
        except InsufficientFundsError:
            logger.debug(
                f"Skipping BUY {signal.ticker}: insufficient funds "
                f"(have {self._cash_balance}, need {price_per_share} × {quantity})"
            )
            return None

        # Update state
        self._cash_balance = self._cash_balance.subtract(
            transaction.cash_change.absolute()
        )
        current_qty = self._holdings.get(signal.ticker, Quantity(Decimal("0")))
        self._holdings[signal.ticker] = current_qty.add(quantity)
        self._transactions.append(transaction)

        return transaction

    def _apply_sell(
        self,
        signal: TradeSignal,
        price_per_share: Money,
        timestamp: datetime,
    ) -> Transaction | None:
        """Apply a SELL signal."""
        current_qty = self._holdings.get(signal.ticker, Quantity(Decimal("0")))

        if signal.quantity is not None:
            quantity = Quantity(signal.quantity)
        else:
            # Sell by amount — resolve to shares
            assert signal.amount is not None
            if price_per_share.amount <= Decimal("0"):
                return None
            raw_qty = signal.amount / price_per_share.amount
            floored = raw_qty.to_integral_value(rounding=ROUND_DOWN)
            if floored <= Decimal("0"):
                return None
            quantity = Quantity(floored)

        ticker = Ticker(signal.ticker)

        try:
            transaction = create_sell_transaction(
                portfolio_id=self._portfolio_id,
                ticker=ticker,
                quantity=quantity,
                price_per_share=price_per_share,
                current_holding_quantity=current_qty,
                timestamp=timestamp,
            )
        except InsufficientSharesError:
            logger.debug(
                f"Skipping SELL {signal.ticker}: insufficient shares "
                f"(have {current_qty.shares}, need {quantity.shares})"
            )
            return None

        # Update state
        self._cash_balance = self._cash_balance.add(transaction.cash_change)
        new_qty = current_qty.subtract(quantity)
        if new_qty.is_zero():
            self._holdings.pop(signal.ticker, None)
        else:
            self._holdings[signal.ticker] = new_qty
        self._transactions.append(transaction)

        return transaction

    def get_holding_quantity(self, ticker: str) -> Quantity:
        """Get current quantity held for a ticker.

        Args:
            ticker: Stock symbol

        Returns:
            Quantity held (zero if not held)
        """
        return self._holdings.get(ticker, Quantity(Decimal("0")))

    def count_trades(self) -> int:
        """Count BUY and SELL transactions (excludes DEPOSIT/WITHDRAWAL).

        Returns:
            Number of executed trades
        """
        return sum(
            1
            for t in self._transactions
            if t.transaction_type in (TransactionType.BUY, TransactionType.SELL)
        )
