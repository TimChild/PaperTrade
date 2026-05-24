"""add_updated_at_column_to_price_history

Adds ``updated_at`` to ``price_history`` so the data-coverage page's
``last_refresh`` field can reflect when we last upserted a bar for a
ticker — not just when we first inserted it.

Before this migration, ``last_refresh = MAX(price_history.created_at)``.
But ``upsert_price`` updates existing rows in place without bumping
``created_at``, so a successful "Catch up" backfill that re-fetches
~20 years of bars (most of which already exist) shows a stale
``last_refresh`` even though the data has been verified-current.
``updated_at`` is bumped on every upsert (insert OR update) so the
metric tracks the actual operator-action / scheduler-refresh signal.

Migration shape:

1. Add ``updated_at`` as ``nullable=True`` — SQLite can't add a NOT NULL
   column without ``batch_alter_table`` machinery, and we don't need the
   constraint at the schema level since the application always
   populates it via :class:`PriceHistoryModel`'s ``default_factory`` and
   :meth:`SqlAlchemyPriceRepository.upsert_price`.
2. Backfill existing rows: ``SET updated_at = created_at``. This makes
   the metric meaningful for historical data immediately after the
   migration runs — without it, the data-coverage page would show
   ``null`` for every ticker until each one is touched again.

The data-coverage query also defensively ``COALESCE``s
``updated_at`` to ``created_at`` so any future row that slips in
without ``updated_at`` (shouldn't happen, but defense in depth) still
produces a meaningful value.

Revision ID: l002_price_history_updated_at
Revises: l001_backtest_agent_invocations
Create Date: 2026-05-24
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "l002_price_history_updated_at"
down_revision: str | Sequence[str] | None = "l001_backtest_agent_invocations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE: str = "price_history"
_COLUMN: str = "updated_at"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_column(table_name: str, column_name: str) -> bool:
    if not _inspector().has_table(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    """Add ``updated_at`` and backfill from ``created_at``."""
    if not _inspector().has_table(_TABLE):
        raise RuntimeError(
            f"{_TABLE} table is missing — apply earlier migrations before "
            "l002_price_history_updated_at."
        )
    if not _has_column(_TABLE, _COLUMN):
        op.add_column(
            _TABLE,
            sa.Column(_COLUMN, sa.DateTime(), nullable=True),
        )
        # Backfill: the operationally-correct seed is the row's own
        # ``created_at`` — for an existing row that was inserted but
        # never updated, ``updated_at == created_at`` is the truth.
        op.execute(f"UPDATE {_TABLE} SET {_COLUMN} = created_at")


def downgrade() -> None:
    """Drop the ``updated_at`` column."""
    if _has_column(_TABLE, _COLUMN):
        op.drop_column(_TABLE, _COLUMN)
