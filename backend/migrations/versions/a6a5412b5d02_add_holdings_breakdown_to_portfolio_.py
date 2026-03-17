"""add holdings_breakdown to portfolio_snapshots

Revision ID: a6a5412b5d02
Revises: 7ca1e9126eba
Create Date: 2026-03-08 00:15:56.021812

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a6a5412b5d02"
down_revision: str | Sequence[str] | None = "7ca1e9126eba"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    """Add holdings_breakdown JSON column to portfolio_snapshots."""
    if _has_table("portfolio_snapshots") and not _has_column(
        "portfolio_snapshots", "holdings_breakdown"
    ):
        op.add_column(
            "portfolio_snapshots",
            sa.Column("holdings_breakdown", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    """Remove holdings_breakdown column from portfolio_snapshots."""
    if _has_column("portfolio_snapshots", "holdings_breakdown"):
        op.drop_column("portfolio_snapshots", "holdings_breakdown")
