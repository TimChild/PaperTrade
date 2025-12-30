"""add_ticker_watchlist_table

Revision ID: 7ca1e9126eba
Revises: e46ccf3fcc35
Create Date: 2025-12-29 23:58:34.470649

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7ca1e9126eba'
down_revision: Union[str, Sequence[str], None] = 'e46ccf3fcc35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create ticker_watchlist table
    op.create_table(
        'ticker_watchlist',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('priority', sa.Integer(), nullable=False, server_default='100'),
        sa.Column('last_refresh_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_refresh_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refresh_interval_seconds', sa.Integer(), nullable=False, server_default='300'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        # Unique constraint on ticker
        sa.UniqueConstraint('ticker', name='uk_ticker_watchlist_ticker'),
    )
    
    # Create index for refresh queries
    op.create_index('idx_watchlist_next_refresh', 'ticker_watchlist', ['next_refresh_at'])
    
    # Pre-populate with common stocks
    op.execute("""
        INSERT INTO ticker_watchlist (ticker, priority) VALUES
            ('AAPL', 100),
            ('GOOGL', 100),
            ('MSFT', 100),
            ('AMZN', 100),
            ('TSLA', 90),
            ('NVDA', 90),
            ('META', 90)
    """)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('idx_watchlist_next_refresh', table_name='ticker_watchlist')
    op.drop_table('ticker_watchlist')
