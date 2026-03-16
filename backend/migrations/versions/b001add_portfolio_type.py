"""add_portfolio_type_to_portfolios

Revision ID: b001add_portfolio_type
Revises: a6a5412b5d02
Create Date: 2026-03-08

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b001add_portfolio_type"
down_revision: str | Sequence[str] | None = "a6a5412b5d02"
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
    """Add portfolio_type column to portfolios table."""
    if _has_table("portfolios") and not _has_column("portfolios", "portfolio_type"):
        op.add_column(
            "portfolios",
            sa.Column(
                "portfolio_type",
                sa.String(length=20),
                nullable=False,
                server_default="PAPER_TRADING",
            ),
        )


def downgrade() -> None:
    """Remove portfolio_type column from portfolios table."""
    if _has_column("portfolios", "portfolio_type"):
        op.drop_column("portfolios", "portfolio_type")
