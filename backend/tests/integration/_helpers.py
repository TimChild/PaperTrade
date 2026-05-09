"""Shared helpers for integration tests.

Helpers here are imported explicitly by tests; conftest is reserved for
pytest fixtures.
"""

from datetime import UTC, datetime
from uuid import UUID

from sqlmodel.ext.asyncio.session import AsyncSession


async def insert_portfolio(
    session: AsyncSession,
    portfolio_id: UUID,
    *,
    user_id: UUID | None = None,
    name: str = "test-portfolio",
    portfolio_type: str = "PAPER_TRADING",
) -> UUID:
    """Insert a minimal portfolio row so child tables can FK-reference it.

    Many integration tests previously generated bare ``uuid4()`` portfolio
    ids and inserted dependent rows directly. Once foreign-key constraints
    are enforced, those orphan rows get rejected. This helper inserts a
    valid parent portfolio so the test focuses on the dependent-row
    behaviour rather than re-creating boilerplate.

    Args:
        session: The integration-test session.
        portfolio_id: UUID of the portfolio to insert.
        user_id: Optional Clerk-derived user id; defaults to ``portfolio_id``
            (arbitrary — there's no FK on user_id).
        name: Portfolio display name.
        portfolio_type: Portfolio type string.

    Returns:
        The ``portfolio_id`` for convenience.
    """
    from zebu.adapters.outbound.database.models import PortfolioModel

    now = datetime.now(UTC).replace(tzinfo=None)
    session.add(
        PortfolioModel(
            id=portfolio_id,
            user_id=user_id if user_id is not None else portfolio_id,
            name=name,
            created_at=now,
            updated_at=now,
            version=1,
            portfolio_type=portfolio_type,
        )
    )
    await session.flush()
    return portfolio_id
