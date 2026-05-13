"""add_mode_column_to_strategy_condition_triggers

Phase J (Task #213) — Pattern B queue-mode triggers.

Adds the ``mode`` column to ``strategy_condition_triggers``. The column
records how a fired trigger reaches an agent:

* ``direct`` — inline Anthropic Messages API call (existing F-3
  behavior, default for all pre-Phase-J rows).
* ``queue`` — file an URGENT :class:`ExplorationTask` for an out-of-band
  agent (desktop Claude / Gemini CLI / etc.) to claim and process.

The column is NOT NULL with a server-side default of ``'direct'`` so
existing rows fill in cleanly without an explicit backfill — every
pre-existing trigger keeps its prior behavior.

No new indexes — the column is read-only on the hot evaluation path
(the orchestrator branches on it once per fire) and is not a filter
predicate for any list endpoint.

The migration is idempotent (uses inspector-based exists checks,
mirroring the j001 / j002 / f001 / f005 / h001 pattern).

Revision ID: j003_trigger_mode
Revises: j002_backfill_tasks
Create Date: 2026-05-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. ``j003_trigger_mode`` is 17
# chars — well under the 32-char cap on ``alembic_version.version_num``.
# Filename matches.
revision: str = "j003_trigger_mode"
down_revision: str | Sequence[str] | None = "j002_backfill_tasks"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_TABLE: str = "strategy_condition_triggers"
_COLUMN: str = "mode"


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_column(table_name: str, column_name: str) -> bool:
    if not _inspector().has_table(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(column["name"] == column_name for column in columns)


def upgrade() -> None:
    """Add ``mode`` to ``strategy_condition_triggers`` with default ``'direct'``."""
    if not _inspector().has_table(_TABLE):
        raise RuntimeError(
            f"{_TABLE} table is missing — apply earlier migrations before "
            "j003_trigger_mode."
        )
    if not _has_column(_TABLE, _COLUMN):
        op.add_column(
            _TABLE,
            sa.Column(
                _COLUMN,
                sa.String(length=16),
                nullable=False,
                server_default="direct",
            ),
        )


def downgrade() -> None:
    """Drop the ``mode`` column."""
    if _has_column(_TABLE, _COLUMN):
        op.drop_column(_TABLE, _COLUMN)
