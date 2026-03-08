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


def upgrade() -> None:
    """Add portfolio_type column to portfolios table."""
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
    op.drop_column("portfolios", "portfolio_type")
