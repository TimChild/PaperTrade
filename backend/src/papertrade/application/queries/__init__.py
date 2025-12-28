"""Query handlers for read operations (no state modification).

Queries read portfolio state and calculate derived values without
modifying anything. They aggregate data from the transaction ledger.
"""

from papertrade.application.queries.get_portfolio import (
    GetPortfolioHandler,
    GetPortfolioQuery,
    GetPortfolioResult,
)
from papertrade.application.queries.get_portfolio_balance import (
    GetPortfolioBalanceHandler,
    GetPortfolioBalanceQuery,
    GetPortfolioBalanceResult,
)
from papertrade.application.queries.get_portfolio_holdings import (
    GetPortfolioHoldingsHandler,
    GetPortfolioHoldingsQuery,
    GetPortfolioHoldingsResult,
)
from papertrade.application.queries.list_transactions import (
    ListTransactionsHandler,
    ListTransactionsQuery,
    ListTransactionsResult,
)

__all__ = [
    "GetPortfolioQuery",
    "GetPortfolioHandler",
    "GetPortfolioResult",
    "GetPortfolioBalanceQuery",
    "GetPortfolioBalanceHandler",
    "GetPortfolioBalanceResult",
    "GetPortfolioHoldingsQuery",
    "GetPortfolioHoldingsHandler",
    "GetPortfolioHoldingsResult",
    "ListTransactionsQuery",
    "ListTransactionsHandler",
    "ListTransactionsResult",
]
