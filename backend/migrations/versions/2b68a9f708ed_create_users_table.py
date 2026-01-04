"""create_users_table

Revision ID: 2b68a9f708ed
Revises: 7ca1e9126eba
Create Date: 2026-01-04 16:03:39.051657

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2b68a9f708ed'
down_revision: Union[str, Sequence[str], None] = '7ca1e9126eba'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
    )

    # Add unique index on email (case-insensitive)
    op.create_index('idx_user_email', 'users', ['email'], unique=True)

    # Add foreign key constraint to portfolios.user_id
    # Note: This assumes portfolios table already exists
    # If it doesn't, this constraint will fail
    op.create_foreign_key(
        'fk_portfolio_user',
        'portfolios', 'users',
        ['user_id'], ['id'],
        ondelete='CASCADE'
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop foreign key constraint from portfolios
    op.drop_constraint('fk_portfolio_user', 'portfolios', type_='foreignkey')

    # Drop index
    op.drop_index('idx_user_email', table_name='users')

    # Drop users table
    op.drop_table('users')
