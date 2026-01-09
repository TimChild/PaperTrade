"""PortfolioCalculator service - Pure functions for calculating portfolio state."""

from decimal import Decimal

from papertrade.domain.entities.holding import Holding
from papertrade.domain.entities.transaction import Transaction, TransactionType
from papertrade.domain.value_objects.money import Money
from papertrade.domain.value_objects.quantity import Quantity
from papertrade.domain.value_objects.ticker import Ticker


class PortfolioCalculator:
    """Pure functions for calculating portfolio state from transaction history.

    All methods are static and side-effect free - they don't modify input data
    or perform I/O. Portfolio state is derived by aggregating the transaction ledger.
    """

    @staticmethod
    def calculate_cash_balance(transactions: list[Transaction]) -> Money:
        """Calculate current cash balance by summing all cash_change values.

        Args:
            transactions: List of transactions (in any order)

        Returns:
            Current cash balance (default USD if no transactions)
        """
        if not transactions:
            return Money(Decimal("0.00"), "USD")

        # Sum all cash changes
        total = Decimal("0.00")
        currency = transactions[0].cash_change.currency

        for transaction in transactions:
            total += transaction.cash_change.amount

        return Money(total, currency)

    @staticmethod
    def calculate_holdings(transactions: list[Transaction]) -> list[Holding]:
        """Derive current stock positions from transaction history.

        For each unique ticker:
        - Process BUY transactions: accumulate shares and cost
        - Process SELL transactions: reduce shares and cost proportionally
        - If final quantity > 0, create Holding

        Args:
            transactions: List of transactions (processed in chronological order)

        Returns:
            List of Holdings with non-zero quantities
        """
        # Group transactions by ticker
        holdings_by_ticker: dict[Ticker, tuple[Quantity, Money]] = {}

        # Sort transactions by timestamp to process chronologically
        sorted_transactions = sorted(transactions, key=lambda t: t.timestamp)

        for transaction in sorted_transactions:
            if transaction.transaction_type not in (
                TransactionType.BUY,
                TransactionType.SELL,
            ):
                continue

            ticker = transaction.ticker
            if ticker is None:
                continue  # Skip non-trade transactions

            quantity = transaction.quantity
            price = transaction.price_per_share

            if quantity is None or price is None:
                continue  # Skip invalid trade data

            # Get current holding state
            if ticker not in holdings_by_ticker:
                holdings_by_ticker[ticker] = (
                    Quantity(Decimal("0")),
                    Money(Decimal("0.00"), price.currency),
                )

            current_qty, current_cost = holdings_by_ticker[ticker]

            if transaction.transaction_type == TransactionType.BUY:
                # Add shares and cost
                new_qty = current_qty.add(quantity)
                trade_cost = price.multiply(quantity.shares)
                new_cost = current_cost.add(trade_cost)
                holdings_by_ticker[ticker] = (new_qty, new_cost)

            elif transaction.transaction_type == TransactionType.SELL:
                # Reduce shares and cost proportionally
                new_qty = current_qty.subtract(quantity)

                if current_qty.is_zero():
                    # Selling from zero - shouldn't happen in valid data
                    new_cost = current_cost
                else:
                    # Reduce cost basis proportionally
                    # new_cost = current_cost * (new_qty / current_qty)
                    ratio = new_qty.shares / current_qty.shares
                    new_cost = current_cost.multiply(ratio)

                holdings_by_ticker[ticker] = (new_qty, new_cost)

        # Create Holding objects for non-zero positions
        holdings = []
        for ticker, (quantity, cost_basis) in holdings_by_ticker.items():
            if quantity.is_positive():
                holdings.append(
                    Holding(ticker=ticker, quantity=quantity, cost_basis=cost_basis)
                )

        return holdings

    @staticmethod
    def calculate_holding_for_ticker(
        transactions: list[Transaction], ticker: Ticker
    ) -> Holding | None:
        """Calculate position for a specific stock.

        Args:
            transactions: List of transactions
            ticker: Ticker to calculate holding for

        Returns:
            Holding for ticker, or None if no position
        """
        all_holdings = PortfolioCalculator.calculate_holdings(transactions)

        for holding in all_holdings:
            if holding.ticker == ticker:
                return holding

        return None

    @staticmethod
    def calculate_portfolio_value(
        holdings: list[Holding], prices: dict[Ticker, Money]
    ) -> Money:
        """Calculate total value of all holdings at given prices.

        Args:
            holdings: List of current holdings
            prices: Current prices for each ticker

        Returns:
            Total value of all holdings
        """
        if not holdings:
            return Money(Decimal("0.00"), "USD")

        total = Decimal("0.00")
        # Use currency from first price
        currency = next(iter(prices.values())).currency if prices else "USD"

        for holding in holdings:
            price = prices.get(holding.ticker)
            if price:
                # value = quantity * price
                holding_value = price.multiply(holding.quantity.shares)
                total += holding_value.amount

        return Money(total, currency)

    @staticmethod
    def calculate_total_value(cash_balance: Money, holdings_value: Money) -> Money:
        """Calculate total portfolio value (cash + holdings).

        Args:
            cash_balance: Current cash balance
            holdings_value: Total value of holdings

        Returns:
            Total portfolio value
        """
        return cash_balance.add(holdings_value)

    @staticmethod
    def calculate_daily_change(
        holdings: list[Holding],
        current_prices: dict[Ticker, Money],
        previous_prices: dict[Ticker, Money],
    ) -> tuple[Money, Decimal]:
        """Calculate daily change in holdings value.

        Calculates the change in portfolio value between previous close and current
        prices. Only holdings value changes; cash balance remains constant.

        Args:
            holdings: List of current holdings
            current_prices: Current market prices by ticker
            previous_prices: Previous day close prices by ticker

        Returns:
            Tuple of (change_amount, change_percent)
            Example: (Money(Decimal("45.32"), "USD"), Decimal("2.14"))
        """
        # Calculate current and previous holdings values
        current_value = PortfolioCalculator.calculate_portfolio_value(
            holdings, current_prices
        )
        previous_value = PortfolioCalculator.calculate_portfolio_value(
            holdings, previous_prices
        )

        # Calculate change amount
        change_amount = current_value.subtract(previous_value)

        # Calculate change percent (avoid division by zero)
        if previous_value.amount == Decimal("0"):
            change_percent = Decimal("0.00")
        else:
            # (change / previous) * 100, rounded to 2 decimal places
            change_percent = (
                (change_amount.amount / previous_value.amount) * Decimal("100")
            ).quantize(Decimal("0.01"))

        return change_amount, change_percent
