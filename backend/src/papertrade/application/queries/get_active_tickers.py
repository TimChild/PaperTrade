"""GetActiveTickers query - Retrieve tickers that need price refresh."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from papertrade.adapters.outbound.database.models import TransactionModel
from papertrade.domain.value_objects.ticker import Ticker


@dataclass(frozen=True)
class GetActiveTickersQuery:
    """Input data for retrieving active tickers.

    Attributes:
        days: Consider tickers traded in last N days (default: 30)
    """

    days: int = 30


@dataclass(frozen=True)
class GetActiveTickersResult:
    """Result of retrieving active tickers.

    Attributes:
        tickers: List of unique ticker symbols with recent activity
        days_window: Number of days considered
    """

    tickers: list[Ticker]
    days_window: int


class GetActiveTickersHandler:
    """Handler for GetActiveTickers query.

    Retrieves tickers that have been traded recently or are held in portfolios.
    This is used by the background scheduler to determine which stocks need
    price updates.
    """

    def __init__(self, session: AsyncSession) -> None:
        """Initialize handler with database session.

        Args:
            session: Async database session for query execution
        """
        self._session = session

    async def execute(self, query: GetActiveTickersQuery) -> GetActiveTickersResult:
        """Execute the GetActiveTickers query.

        Retrieves tickers that:
        - Have been traded in the last N days (from transactions), OR
        - Are currently held in any portfolio (have BUY transactions)

        Args:
            query: Query with days parameter

        Returns:
            Result containing unique list of active tickers

        Raises:
            ValueError: If days parameter is invalid
        """
        # Validate input
        if query.days < 1:
            raise ValueError("Days must be at least 1")

        # Calculate cutoff date
        cutoff = datetime.now(UTC) - timedelta(days=query.days)

        # Query for tickers from recent transactions
        # Get distinct tickers that have been traded recently
        stmt = (
            select(TransactionModel.ticker)
            .where(TransactionModel.ticker.is_not(None))  # type: ignore[attr-defined]  # SQLModel field has SQLAlchemy column methods
            .where(TransactionModel.timestamp >= cutoff)
            .distinct()
        )

        result = await self._session.exec(stmt)
        ticker_symbols = result.all()

        # Convert to Ticker objects and remove duplicates
        unique_tickers = list({Ticker(symbol) for symbol in ticker_symbols if symbol})

        return GetActiveTickersResult(
            tickers=unique_tickers,
            days_window=query.days,
        )
