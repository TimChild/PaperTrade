"""Trade factory - Pure domain functions for creating validated transactions."""

from datetime import datetime
from uuid import UUID, uuid4

from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.exceptions import InsufficientFundsError, InsufficientSharesError
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.ticker import Ticker


def create_buy_transaction(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: Quantity,
    price_per_share: Money,
    cash_balance: Money,
    timestamp: datetime,
    notes: str | None = None,
) -> Transaction:
    """Create a validated BUY transaction.

    Pure domain function that validates sufficient funds and creates
    a BUY transaction. Used by both the BuyStockHandler (live trading)
    and BacktestTransactionBuilder (backtesting).

    Args:
        portfolio_id: Target portfolio
        ticker: Stock to buy
        quantity: Number of shares
        price_per_share: Price per share
        cash_balance: Current cash available
        timestamp: When the trade occurs
        notes: Optional trade notes

    Returns:
        Transaction domain entity

    Raises:
        InsufficientFundsError: If cash_balance < total_cost
    """
    total_cost = price_per_share.multiply(quantity.shares)
    if cash_balance < total_cost:
        raise InsufficientFundsError(available=cash_balance, required=total_cost)

    return Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.BUY,
        timestamp=timestamp,
        cash_change=total_cost.negate(),
        ticker=ticker,
        quantity=quantity,
        price_per_share=price_per_share,
        notes=notes,
    )


def create_sell_transaction(
    portfolio_id: UUID,
    ticker: Ticker,
    quantity: Quantity,
    price_per_share: Money,
    current_holding_quantity: Quantity,
    timestamp: datetime,
    notes: str | None = None,
) -> Transaction:
    """Create a validated SELL transaction.

    Pure domain function that validates sufficient shares and creates
    a SELL transaction.

    Args:
        portfolio_id: Target portfolio
        ticker: Stock to sell
        quantity: Number of shares to sell
        price_per_share: Price per share
        current_holding_quantity: Shares currently held for this ticker
        timestamp: When the trade occurs
        notes: Optional trade notes

    Returns:
        Transaction domain entity

    Raises:
        InsufficientSharesError: If current_holding_quantity < quantity
    """
    if current_holding_quantity < quantity:
        raise InsufficientSharesError(
            ticker=ticker.symbol,
            available=current_holding_quantity,
            required=quantity,
        )

    total_proceeds = price_per_share.multiply(quantity.shares)

    return Transaction(
        id=uuid4(),
        portfolio_id=portfolio_id,
        transaction_type=TransactionType.SELL,
        timestamp=timestamp,
        cash_change=total_proceeds,
        ticker=ticker,
        quantity=quantity,
        price_per_share=price_per_share,
        notes=notes,
    )
