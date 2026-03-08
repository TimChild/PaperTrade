"""add holdings_breakdown to portfolio_snapshots

Revision ID: a6a5412b5d02
Revises: 7ca1e9126eba
Create Date: 2026-03-08 00:15:56.021812

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'a6a5412b5d02'
down_revision: Union[str, Sequence[str], None] = '7ca1e9126eba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add holdings_breakdown JSON column to portfolio_snapshots."""
    op.add_column(
        'portfolio_snapshots',
        sa.Column('holdings_breakdown', sa.JSON(), nullable=True),
    )


def downgrade() -> None:
    """Remove holdings_breakdown column from portfolio_snapshots."""
    op.drop_column('portfolio_snapshots', 'holdings_breakdown')

