"""add_strategy_condition_triggers_and_trigger_fire_records

Phase F-1 — adds the two tables for the trigger system:

* ``strategy_condition_triggers`` — wakes the agent when a condition
  fires on an attached :class:`StrategyActivation`. Carries the
  discriminated condition params as a JSON column, the agent prompt,
  cooldown, status, priority, optional default API key + expiry.

* ``trigger_fire_records`` — append-only audit row written each time
  the evaluator fires a trigger. Records the condition snapshot, the
  agent decision (post-guardrail), the resulting trade / modify
  payload / exploration task pointer, and the API key the agent acted
  under.

See ``docs/architecture/phase-f-agent-in-the-loop.md`` §1 for the full
domain contract.

Indexes:

* ``idx_trigger_activation_status`` — fast trigger lookup per activation.
* ``idx_trigger_status_last_fired`` — evaluator scan path.
* ``idx_trigger_user_status`` — backs the dashboard's "my triggers" view.
* ``idx_trigger_fire_trigger_fired_at`` — backs ``list_for_trigger``.
* ``idx_trigger_fire_activation_fired_at`` — backs ``list_for_activation``.

Foreign-key behaviour:

* ``strategy_condition_triggers.activation_id`` -> ``strategy_activations.id``
  ON DELETE CASCADE.
* ``strategy_condition_triggers.default_api_key_id`` -> ``api_keys.id``
  ON DELETE SET NULL.
* ``trigger_fire_records.trigger_id`` -> ``strategy_condition_triggers.id``
  ON DELETE CASCADE.
* ``trigger_fire_records.activation_id`` -> ``strategy_activations.id``
  ON DELETE CASCADE.
* ``trigger_fire_records.resulting_trade_id`` -> ``transactions.id``
  ON DELETE SET NULL.
* ``trigger_fire_records.resulting_exploration_task_id`` ->
  ``exploration_tasks.id`` ON DELETE SET NULL.
* ``trigger_fire_records.api_key_id_used`` -> ``api_keys.id``
  ON DELETE RESTRICT — never lose attribution.

The migration is idempotent (uses inspector-based exists checks for both
tables and their indexes, mirroring the pattern in ``c001`` / ``c002``).

Revision ID: f001_trigger_entities
Revises: c002_add_api_keys
Create Date: 2026-05-10
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic. Note: the revision id is 21
# characters — well under the 32-character cap on
# ``alembic_version.version_num``. Filename matches.
revision: str = "f001_trigger_entities"
down_revision: str | Sequence[str] | None = "c002_add_api_keys"
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
    """Create ``strategy_condition_triggers`` + ``trigger_fire_records``."""
    # Sanity-check the FK targets exist before we declare constraints.
    # An early-stage clone that hasn't run the prior migrations will
    # surface a clear error here rather than a confusing FK creation
    # failure inside ``op.create_table``.
    for required in ("strategy_activations", "api_keys"):
        if not _has_table(required):
            raise RuntimeError(
                f"{required} table is missing — apply earlier migrations "
                "before f001_trigger_entities."
            )

    # ------------------------------------------------------------------
    # strategy_condition_triggers
    # ------------------------------------------------------------------
    if not _has_table("strategy_condition_triggers"):
        op.create_table(
            "strategy_condition_triggers",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("activation_id", sa.Uuid(), nullable=False),
            sa.Column("user_id", sa.Uuid(), nullable=False),
            sa.Column("condition_type", sa.String(length=40), nullable=False),
            sa.Column("condition_params", sa.JSON(), nullable=False),
            sa.Column("agent_prompt", sa.String(length=4000), nullable=False),
            sa.Column(
                "cooldown_seconds",
                sa.Integer(),
                nullable=False,
                server_default="21600",
            ),
            sa.Column("last_fired_at", sa.DateTime(), nullable=True),
            sa.Column("status", sa.String(length=30), nullable=False),
            sa.Column(
                "priority",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
            sa.Column("default_api_key_id", sa.Uuid(), nullable=True),
            sa.Column("expires_at", sa.DateTime(), nullable=True),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.Column("created_by", sa.Uuid(), nullable=False),
            sa.Column("updated_at", sa.DateTime(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["activation_id"],
                ["strategy_activations.id"],
                name="fk_trigger_activation",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["default_api_key_id"],
                ["api_keys.id"],
                name="fk_trigger_default_api_key",
                ondelete="SET NULL",
            ),
        )

    if not _has_index("strategy_condition_triggers", "idx_trigger_activation_status"):
        op.create_index(
            "idx_trigger_activation_status",
            "strategy_condition_triggers",
            ["activation_id", "status"],
        )

    if not _has_index("strategy_condition_triggers", "idx_trigger_status_last_fired"):
        op.create_index(
            "idx_trigger_status_last_fired",
            "strategy_condition_triggers",
            ["status", "last_fired_at"],
        )

    if not _has_index("strategy_condition_triggers", "idx_trigger_user_status"):
        op.create_index(
            "idx_trigger_user_status",
            "strategy_condition_triggers",
            ["user_id", "status"],
        )

    # ------------------------------------------------------------------
    # trigger_fire_records (append-only audit)
    # ------------------------------------------------------------------
    if not _has_table("trigger_fire_records"):
        op.create_table(
            "trigger_fire_records",
            sa.Column("id", sa.Uuid(), nullable=False),
            sa.Column("trigger_id", sa.Uuid(), nullable=False),
            sa.Column("activation_id", sa.Uuid(), nullable=False),
            sa.Column("fired_at", sa.DateTime(), nullable=False),
            sa.Column("condition_evaluation_data", sa.JSON(), nullable=False),
            sa.Column("agent_invocation_id", sa.String(length=200), nullable=True),
            sa.Column("agent_response", sa.String(length=30), nullable=False),
            sa.Column("agent_response_raw", sa.String(length=8000), nullable=False),
            sa.Column("resulting_trade_id", sa.Uuid(), nullable=True),
            sa.Column("resulting_modify_payload", sa.JSON(), nullable=True),
            sa.Column("resulting_exploration_task_id", sa.Uuid(), nullable=True),
            sa.Column("latency_ms", sa.Integer(), nullable=False),
            sa.Column("api_key_id_used", sa.Uuid(), nullable=False),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(
                ["trigger_id"],
                ["strategy_condition_triggers.id"],
                name="fk_trigger_fire_trigger",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["activation_id"],
                ["strategy_activations.id"],
                name="fk_trigger_fire_activation",
                ondelete="CASCADE",
            ),
            sa.ForeignKeyConstraint(
                ["resulting_trade_id"],
                ["transactions.id"],
                name="fk_trigger_fire_trade",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["resulting_exploration_task_id"],
                ["exploration_tasks.id"],
                name="fk_trigger_fire_exploration_task",
                ondelete="SET NULL",
            ),
            sa.ForeignKeyConstraint(
                ["api_key_id_used"],
                ["api_keys.id"],
                name="fk_trigger_fire_api_key",
                ondelete="RESTRICT",
            ),
        )

    if not _has_index("trigger_fire_records", "idx_trigger_fire_trigger_fired_at"):
        op.create_index(
            "idx_trigger_fire_trigger_fired_at",
            "trigger_fire_records",
            ["trigger_id", "fired_at"],
        )

    if not _has_index("trigger_fire_records", "idx_trigger_fire_activation_fired_at"):
        op.create_index(
            "idx_trigger_fire_activation_fired_at",
            "trigger_fire_records",
            ["activation_id", "fired_at"],
        )


def downgrade() -> None:
    """Drop both tables and their indexes (reverse order).

    Drops indexes first, then the tables. FK constraints are dropped
    implicitly when the tables are dropped — SQLite cannot ALTER a
    constraint and PostgreSQL drops dependent constraints on table drop.
    """
    if _has_index("trigger_fire_records", "idx_trigger_fire_activation_fired_at"):
        op.drop_index(
            "idx_trigger_fire_activation_fired_at",
            table_name="trigger_fire_records",
        )
    if _has_index("trigger_fire_records", "idx_trigger_fire_trigger_fired_at"):
        op.drop_index(
            "idx_trigger_fire_trigger_fired_at",
            table_name="trigger_fire_records",
        )
    if _has_table("trigger_fire_records"):
        op.drop_table("trigger_fire_records")

    if _has_index("strategy_condition_triggers", "idx_trigger_user_status"):
        op.drop_index(
            "idx_trigger_user_status",
            table_name="strategy_condition_triggers",
        )
    if _has_index("strategy_condition_triggers", "idx_trigger_status_last_fired"):
        op.drop_index(
            "idx_trigger_status_last_fired",
            table_name="strategy_condition_triggers",
        )
    if _has_index("strategy_condition_triggers", "idx_trigger_activation_status"):
        op.drop_index(
            "idx_trigger_activation_status",
            table_name="strategy_condition_triggers",
        )
    if _has_table("strategy_condition_triggers"):
        op.drop_table("strategy_condition_triggers")
