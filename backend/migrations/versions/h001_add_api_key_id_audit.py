"""add_api_key_id_to_writable_tables

Phase H2 — adds a nullable ``api_key_id`` column (FK -> ``api_keys.id``,
``ON DELETE SET NULL``) to the five writable tables that record actor
activity:

* ``transactions``
* ``strategies``
* ``strategy_activations``
* ``backtest_runs``
* ``exploration_tasks``

The column distinguishes API-key-authenticated writes (agent / scheduled
task / MCP server) from Clerk-Bearer-authenticated writes (human via UI).
The recent-activity feed at ``GET /api/v1/activity`` joins on this column
to surface the API-key label as the actor identity. Existing rows have
``NULL`` (= "human via Clerk") and no backfill is required.

``ON DELETE SET NULL`` is deliberate — a revoked / rotated API key must
not erase the history of writes it produced; it just detaches the
credential reference. The activity feed renders rows with ``NULL`` as
``actor_kind="user"``.

The five chosen tables are the trade-able ones explicitly named in the
Phase H2 task spec; scheduler-driven tables (``portfolio_snapshots``,
``price_history``, ``ticker_watchlist``) and the auth tables
(``portfolios``, ``api_keys`` itself) are intentionally NOT annotated.

Revision ID: h001_add_api_key_id_audit
Revises: c002_add_api_keys
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "h001_add_api_key_id_audit"
down_revision: str | Sequence[str] | None = "c002_add_api_keys"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables to annotate. Each entry is the table name; the FK constraint name
# is derived as ``fk_<table>_api_key_id_api_keys`` for consistency with the
# convention used by ``d26cec7cdf69``.
_WRITABLE_TABLES: tuple[str, ...] = (
    "transactions",
    "strategies",
    "strategy_activations",
    "backtest_runs",
    "exploration_tasks",
)


def _inspector() -> sa.Inspector:
    return sa.inspect(op.get_bind())


def _has_table(table_name: str) -> bool:
    return _inspector().has_table(table_name)


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    columns = _inspector().get_columns(table_name)
    return any(col["name"] == column_name for col in columns)


def _has_fk(table_name: str, fk_name: str) -> bool:
    if not _has_table(table_name):
        return False
    fks = _inspector().get_foreign_keys(table_name)
    return any(fk.get("name") == fk_name for fk in fks)


def upgrade() -> None:
    """Add nullable ``api_key_id`` + FK to the five writable tables.

    Uses ``batch_alter_table`` so SQLite (which cannot ALTER an existing
    table to add a foreign key) gets a transparent CREATE+COPY+DROP rebuild
    while Postgres gets a normal ALTER.
    """
    if not _has_table("api_keys"):
        # The api_keys table is the FK target; if it's not present yet the
        # earlier migration (c002) hasn't run. Bail with a clear message
        # rather than letting the FK creation fail mid-batch.
        raise RuntimeError(
            "api_keys table is missing — run migration c002_add_api_keys "
            "before applying h001."
        )

    for table in _WRITABLE_TABLES:
        if not _has_table(table):
            # Fresh databases that don't have every table yet skip cleanly
            # (e.g. an early-stage clone where backtest_runs hasn't been
            # created). The matching from-domain code paths only run once
            # the table exists, so there's nothing to back-fill.
            continue

        column_name = "api_key_id"
        fk_name = f"fk_{table}_api_key_id_api_keys"

        if not _has_column(table, column_name):
            with op.batch_alter_table(table) as batch:
                batch.add_column(
                    sa.Column(column_name, sa.Uuid(), nullable=True),
                )

        if not _has_fk(table, fk_name):
            with op.batch_alter_table(table) as batch:
                batch.create_foreign_key(
                    fk_name,
                    "api_keys",
                    [column_name],
                    ["id"],
                    ondelete="SET NULL",
                )


def downgrade() -> None:
    """Drop the ``api_key_id`` column + FK from each writable table.

    Drops the FK constraint first, then the column, in reverse order
    relative to ``upgrade``. SQLite handles both via batch_alter_table's
    rebuild path.
    """
    for table in reversed(_WRITABLE_TABLES):
        column_name = "api_key_id"
        fk_name = f"fk_{table}_api_key_id_api_keys"

        if _has_fk(table, fk_name):
            with op.batch_alter_table(table) as batch:
                batch.drop_constraint(fk_name, type_="foreignkey")

        if _has_column(table, column_name):
            with op.batch_alter_table(table) as batch:
                batch.drop_column(column_name)
