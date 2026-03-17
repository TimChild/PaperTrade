"""create_core_portfolio_tables

Revision ID: c9b7d8e0f1a2
Revises:
Create Date: 2026-03-16

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c9b7d8e0f1a2"
down_revision: str | Sequence[str] | None = None
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
    """Create the original portfolio tables that predate Alembic usage."""
    if not _has_table("portfolios"):
        op.create_table(
            "portfolios",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("name", sa.String(length=100), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.Column("version", sa.Integer(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index("portfolios", "idx_portfolio_user_id"):
        op.create_index("idx_portfolio_user_id", "portfolios", ["user_id"])

    if not _has_table("transactions"):
        op.create_table(
            "transactions",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("portfolio_id", sa.Uuid(), nullable=False),
            sa.Column("transaction_type", sa.String(length=20), nullable=False),
            sa.Column("timestamp", sa.DateTime(), nullable=False),
            sa.Column(
                "cash_change_amount",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
            ),
            sa.Column("cash_change_currency", sa.String(length=3), nullable=False),
            sa.Column("ticker", sa.String(length=5), nullable=True),
            sa.Column("quantity", sa.Numeric(precision=15, scale=4), nullable=True),
            sa.Column(
                "price_per_share_amount",
                sa.Numeric(precision=15, scale=2),
                nullable=True,
            ),
            sa.Column("price_per_share_currency", sa.String(length=3), nullable=True),
            sa.Column("notes", sa.String(length=500), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index("transactions", "idx_transaction_portfolio_id"):
        op.create_index(
            "idx_transaction_portfolio_id", "transactions", ["portfolio_id"]
        )
    if not _has_index("transactions", "idx_transaction_timestamp"):
        op.create_index("idx_transaction_timestamp", "transactions", ["timestamp"])
    if not _has_index("transactions", "idx_transaction_portfolio_timestamp"):
        op.create_index(
            "idx_transaction_portfolio_timestamp",
            "transactions",
            ["portfolio_id", "timestamp"],
        )

    if not _has_table("portfolio_snapshots"):
        op.create_table(
            "portfolio_snapshots",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("portfolio_id", sa.Uuid(), nullable=False),
            sa.Column("snapshot_date", sa.Date(), nullable=False),
            sa.Column(
                "total_value",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
            ),
            sa.Column(
                "cash_balance",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
            ),
            sa.Column(
                "holdings_value",
                sa.Numeric(precision=15, scale=2),
                nullable=False,
            ),
            sa.Column("holdings_count", sa.Integer(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index("portfolio_snapshots", "idx_snapshot_portfolio_date"):
        op.create_index(
            "idx_snapshot_portfolio_date",
            "portfolio_snapshots",
            ["portfolio_id", "snapshot_date"],
        )
    if not _has_index("portfolio_snapshots", "idx_snapshot_date"):
        op.create_index("idx_snapshot_date", "portfolio_snapshots", ["snapshot_date"])


def downgrade() -> None:
    """Drop the original portfolio tables."""
    if _has_index("portfolio_snapshots", "idx_snapshot_date"):
        op.drop_index("idx_snapshot_date", table_name="portfolio_snapshots")
    if _has_index("portfolio_snapshots", "idx_snapshot_portfolio_date"):
        op.drop_index("idx_snapshot_portfolio_date", table_name="portfolio_snapshots")
    if _has_table("portfolio_snapshots"):
        op.drop_table("portfolio_snapshots")

    if _has_index("transactions", "idx_transaction_portfolio_timestamp"):
        op.drop_index("idx_transaction_portfolio_timestamp", table_name="transactions")
    if _has_index("transactions", "idx_transaction_timestamp"):
        op.drop_index("idx_transaction_timestamp", table_name="transactions")
    if _has_index("transactions", "idx_transaction_portfolio_id"):
        op.drop_index("idx_transaction_portfolio_id", table_name="transactions")
    if _has_table("transactions"):
        op.drop_table("transactions")

    if _has_index("portfolios", "idx_portfolio_user_id"):
        op.drop_index("idx_portfolio_user_id", table_name="portfolios")
    if _has_table("portfolios"):
        op.drop_table("portfolios")
