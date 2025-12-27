"""Portfolio calculator service - Computes portfolio state from transactions."""

from __future__ import annotations

from decimal import Decimal

from papertrade.domain.entities import Holding, Transaction, TransactionType
from papertrade.domain.value_objects import Money, Quantity, Ticker


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
        """
        # Track shares and total cost per ticker
        positions: dict[Ticker, dict[str, Decimal]] = {}

        for txn in transactions:
            if txn.type not in (TransactionType.BUY, TransactionType.SELL):
                continue

            # These should always be present for BUY/SELL transactions
            assert txn.ticker is not None
            assert txn.quantity is not None
            assert txn.price_per_share is not None

            ticker = txn.ticker

            # Initialize position if needed
            if ticker not in positions:
                positions[ticker] = {
                    "quantity": Decimal("0"),
                    "total_cost": Decimal("0.00"),
                }

            if txn.type == TransactionType.BUY:
                # Add shares and cost
                positions[ticker]["quantity"] += txn.quantity.value
                positions[ticker]["total_cost"] += txn.amount.amount
            elif txn.type == TransactionType.SELL:
                # Remove shares proportionally from cost basis
                current_qty = positions[ticker]["quantity"]
                if current_qty > 0:
                    # Reduce cost basis proportionally
                    sell_ratio = txn.quantity.value / current_qty
                    positions[ticker]["total_cost"] -= (
                        positions[ticker]["total_cost"] * sell_ratio
                    )
                positions[ticker]["quantity"] -= txn.quantity.value

        # Convert to Holding objects
        holdings: list[Holding] = []
        for ticker, position in positions.items():
            qty = position["quantity"]
            if qty > 0:
                # Calculate average cost per share
                avg_cost = (position["total_cost"] / qty).quantize(Decimal("0.01"))
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
