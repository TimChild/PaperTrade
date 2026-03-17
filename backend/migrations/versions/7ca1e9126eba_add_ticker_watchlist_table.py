"""add_ticker_watchlist_table

Revision ID: 7ca1e9126eba
Revises: e46ccf3fcc35
Create Date: 2025-12-29 23:58:34.470649

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "7ca1e9126eba"
down_revision: str | Sequence[str] | None = "e46ccf3fcc35"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_index(table_name: str, index_name: str) -> bool:
    if not _has_table(table_name):
        return False
    indexes = _inspector().get_indexes(table_name)
    return any(index["name"] == index_name for index in indexes)


def upgrade() -> None:
    """Upgrade schema."""
    if not _has_table("ticker_watchlist"):
        op.create_table(
            "ticker_watchlist",
            sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
            sa.Column("ticker", sa.String(length=10), nullable=False),
            sa.Column("priority", sa.Integer(), nullable=False, server_default="100"),
            sa.Column("last_refresh_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column("next_refresh_at", sa.DateTime(timezone=True), nullable=True),
            sa.Column(
                "refresh_interval_seconds",
                sa.Integer(),
                nullable=False,
                server_default="300",
            ),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default="1"),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column(
                "updated_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.PrimaryKeyConstraint("id"),
            sa.UniqueConstraint("ticker", name="uk_ticker_watchlist_ticker"),
        )

    if not _has_index("ticker_watchlist", "idx_watchlist_next_refresh"):
        op.create_index(
            "idx_watchlist_next_refresh",
            "ticker_watchlist",
            ["next_refresh_at"],
        )

    # Pre-populate with common stocks without duplicating existing rows.
    for ticker, priority in [
        ("AAPL", 100),
        ("GOOGL", 100),
        ("MSFT", 100),
        ("AMZN", 100),
        ("TSLA", 90),
        ("NVDA", 90),
        ("META", 90),
    ]:
        op.execute(
            sa.text(
                """
                INSERT INTO ticker_watchlist (ticker, priority)
                VALUES (:ticker, :priority)
                ON CONFLICT (ticker) DO NOTHING
                """
            ).bindparams(ticker=ticker, priority=priority)
        )


def downgrade() -> None:
    """Downgrade schema."""
    if _has_index("ticker_watchlist", "idx_watchlist_next_refresh"):
        op.drop_index("idx_watchlist_next_refresh", table_name="ticker_watchlist")
    if _has_table("ticker_watchlist"):
        op.drop_table("ticker_watchlist")
