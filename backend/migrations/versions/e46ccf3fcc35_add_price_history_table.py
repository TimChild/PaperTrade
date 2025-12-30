"""add_price_history_table

Revision ID: e46ccf3fcc35
Revises: 
Create Date: 2025-12-29 23:58:27.842538

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e46ccf3fcc35'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create price_history table
    op.create_table(
        'price_history',
        sa.Column('id', sa.Integer(), nullable=False, autoincrement=True),
        sa.Column('ticker', sa.String(length=10), nullable=False),
        sa.Column('price_amount', sa.Numeric(precision=18, scale=2), nullable=False),
        sa.Column('price_currency', sa.String(length=3), nullable=False, server_default='USD'),
        sa.Column('timestamp', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source', sa.String(length=50), nullable=False),
        sa.Column('interval', sa.String(length=10), nullable=False),
        # Optional OHLCV data
        sa.Column('open_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('open_currency', sa.String(length=3), nullable=True),
        sa.Column('high_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('high_currency', sa.String(length=3), nullable=True),
        sa.Column('low_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('low_currency', sa.String(length=3), nullable=True),
        sa.Column('close_amount', sa.Numeric(precision=18, scale=2), nullable=True),
        sa.Column('close_currency', sa.String(length=3), nullable=True),
        sa.Column('volume', sa.BigInteger(), nullable=True),
        # Metadata
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        # Primary key
        sa.PrimaryKeyConstraint('id'),
        # Check constraints
        sa.CheckConstraint('price_amount > 0', name='price_positive'),
    )
    
    # Create indexes for performance
    op.create_index('idx_price_history_ticker_timestamp', 'price_history', ['ticker', 'timestamp'])
    op.create_index('idx_price_history_ticker_interval_timestamp', 'price_history', 
                    ['ticker', 'interval', 'timestamp'])
    
    # Create unique constraint (one price per ticker per timestamp per interval)
    op.create_index('uk_price_history', 'price_history', 
                    ['ticker', 'timestamp', 'source', 'interval'], 
                    unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uk_price_history', table_name='price_history')
    op.drop_index('idx_price_history_ticker_interval_timestamp', table_name='price_history')
    op.drop_index('idx_price_history_ticker_timestamp', table_name='price_history')
    op.drop_table('price_history')
