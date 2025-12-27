"""Portfolio calculator service - Computes portfolio state from transactions."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from papertrade.domain.entities import Holding, Transaction, TransactionType
from papertrade.domain.exceptions import InsufficientSharesError
from papertrade.domain.value_objects import Money, Quantity, Ticker


@dataclass
class _Position:
    """Internal class to track position state during calculation."""

    quantity: Decimal
    total_cost: Decimal


class PortfolioCalculator:
    """Calculates portfolio state from transaction history.

    This is a stateless domain service that derives portfolio state
    (cash balance, holdings, total value) from the transaction ledger.
    """

    @staticmethod
    def calculate_cash_balance(transactions: list[Transaction]) -> Money:
        """Calculate the current cash balance from transaction history.

        Args:
            transactions: List of all transactions in the portfolio.

        Returns:
            Money representing the current cash balance.

        Note:
            - DEPOSIT adds cash
            - WITHDRAWAL subtracts cash
            - BUY subtracts cash
            - SELL adds cash
            - DIVIDEND adds cash
            - FEE subtracts cash
        """
        if not transactions:
            return Money(Decimal("0.00"), "USD")

        # Start with zero balance
        balance = Money(Decimal("0.00"), "USD")

        for txn in transactions:
            if txn.type == TransactionType.DEPOSIT:
                balance = balance + txn.amount
            elif (
                txn.type == TransactionType.WITHDRAWAL
                or txn.type == TransactionType.BUY
            ):
                balance = balance - txn.amount
            elif (
                txn.type == TransactionType.SELL or txn.type == TransactionType.DIVIDEND
            ):
                balance = balance + txn.amount
            elif txn.type == TransactionType.FEE:
                balance = balance - txn.amount

        return balance

    @staticmethod
    def calculate_holdings(transactions: list[Transaction]) -> list[Holding]:
        """Calculate current holdings from transaction history.

        Args:
            transactions: List of all transactions in the portfolio.

        Returns:
            List of Holding objects representing current positions.

        Note:
            Holdings with zero quantity are excluded from the result.

        Raises:
            InsufficientSharesError: If attempting to sell more shares than owned.
        """
        # Track shares and total cost per ticker
        positions: dict[Ticker, _Position] = {}

        for txn in transactions:
            if txn.type not in (TransactionType.BUY, TransactionType.SELL):
                continue

            # Type narrowing: these fields are guaranteed non-None for BUY/SELL
            if (
                txn.ticker is None
                or txn.quantity is None
                or txn.price_per_share is None
            ):
                raise ValueError(
                    f"BUY/SELL transaction missing required fields: "
                    f"ticker={txn.ticker}, quantity={txn.quantity}, "
                    f"price_per_share={txn.price_per_share}"
                )

            ticker = txn.ticker

            # Initialize position if needed
            if ticker not in positions:
                positions[ticker] = _Position(
                    quantity=Decimal("0"), total_cost=Decimal("0.00")
                )

            if txn.type == TransactionType.BUY:
                # Add shares and cost
                positions[ticker].quantity += txn.quantity.value
                positions[ticker].total_cost += txn.amount.amount
            elif txn.type == TransactionType.SELL:
                current_qty = positions[ticker].quantity

                # Prevent short selling - validate before processing
                if txn.quantity.value > current_qty:
                    raise InsufficientSharesError(
                        f"Cannot sell {txn.quantity.value} shares of {ticker}. "
                        f"Only {current_qty} shares available."
                    )

                # Remove shares proportionally from cost basis
                if current_qty > 0:
                    # Reduce cost basis proportionally
                    sell_ratio = txn.quantity.value / current_qty
                    positions[ticker].total_cost -= (
                        positions[ticker].total_cost * sell_ratio
                    )
                positions[ticker].quantity -= txn.quantity.value

        # Convert to Holding objects
        holdings: list[Holding] = []
        for ticker, position in positions.items():
            qty = position.quantity
            if qty > 0:
                # Calculate average cost per share
                avg_cost = (position.total_cost / qty).quantize(Decimal("0.01"))
                holdings.append(
                    Holding(
                        ticker=ticker,
                        quantity=Quantity(qty),
                        average_cost=Money(avg_cost, "USD"),
                    )
                )

        return holdings

    @staticmethod
    def calculate_total_value(
        holdings: list[Holding],
        prices: dict[Ticker, Money],
        cash_balance: Money,
    ) -> Money:
        """Calculate total portfolio value at given prices.

        Args:
            holdings: List of current holdings.
            prices: Dictionary mapping tickers to current market prices.
            cash_balance: Current cash balance.

        Returns:
            Money representing the total portfolio value.
        """
        total = cash_balance

        for holding in holdings:
            if holding.ticker in prices:
                current_price = prices[holding.ticker]
                holding_value = current_price * holding.quantity.value
                total = total + holding_value

        return total
