"""add_api_keys_table

Phase C2 — adds the ``api_keys`` table for the API-key authentication path.

The table stores hashed API keys (HMAC-SHA256, hex). The raw key never
hits the DB. ``user_id`` is the deterministic UUID derived from the
Clerk user-id; ``clerk_user_id`` is the original Clerk string preserved
so the auth adapter can hand it back as ``AuthenticatedUser.id``.

Revision ID: c002_add_api_keys
Revises: c001add_exploration_tasks
Create Date: 2026-05-09

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c002_add_api_keys"
down_revision: str | Sequence[str] | None = "c001add_exploration_tasks"
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
    """Create the api_keys table and its indexes."""
    if not _has_table("api_keys"):
        op.create_table(
            "api_keys",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("clerk_user_id", sa.String(length=255), nullable=False),
            sa.Column("label", sa.String(length=100), nullable=False),
            sa.Column("key_hash", sa.String(length=128), nullable=False),
            sa.Column("scopes", sa.JSON(), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("last_used_at", sa.DateTime(), nullable=True),
            sa.Column("revoked_at", sa.DateTime(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
        )

    if not _has_index("api_keys", "idx_api_key_user_id"):
        op.create_index("idx_api_key_user_id", "api_keys", ["user_id"])
    if not _has_index("api_keys", "idx_api_key_hash"):
        op.create_index("idx_api_key_hash", "api_keys", ["key_hash"], unique=True)


def downgrade() -> None:
    """Drop the api_keys table and its indexes."""
    if _has_index("api_keys", "idx_api_key_hash"):
        op.drop_index("idx_api_key_hash", table_name="api_keys")
    if _has_index("api_keys", "idx_api_key_user_id"):
        op.drop_index("idx_api_key_user_id", table_name="api_keys")
    if _has_table("api_keys"):
        op.drop_table("api_keys")
