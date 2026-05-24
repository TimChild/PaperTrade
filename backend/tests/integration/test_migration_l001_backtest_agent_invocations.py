"""Migration test for ``l001_backtest_agent_invocations`` (Phase L-1).

Asserts that:

* ``alembic upgrade head`` from the prior head (``j004_audit_cleanup``)
  applies cleanly to a fresh SQLite DB.
* ``alembic downgrade -1`` reverses the table creation AND drops the
  ``agent_invocation_mode`` column on ``backtest_runs``.
* Re-running ``alembic upgrade head`` after the downgrade re-creates
  everything (idempotency).

Runs alembic via its programmatic ``command`` API against a temp-file
SQLite DB. We use the sync ``sqlite:///`` driver because the project's
``migrations/env.py`` branches on the URL prefix — async-only drivers
require ``+asyncpg``.
"""

from __future__ import annotations

import os
from collections.abc import Generator
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.command import downgrade, upgrade
from alembic.config import Config


def _alembic_cfg(db_path: Path) -> Config:
    """Build an Alembic ``Config`` pointing at the project's migrations dir
    and the temp-file SQLite DB.

    NB: we explicitly null out ``config_file_name`` after loading the
    ini's ``alembic`` section so ``env.py``'s ``fileConfig(...)`` call
    no-ops. Otherwise Python's ``logging.config.fileConfig`` runs with
    its default ``disable_existing_loggers=True`` and disables every
    logger created before alembic runs — including domain-entity
    loggers that test fixtures (caplog) elsewhere in the suite assert
    against. The migration only needs the SQL connection; logger
    reconfiguration is a side effect we don't want in tests.
    """
    backend_root = Path(__file__).resolve().parents[2]
    cfg_path = backend_root / "alembic.ini"
    assert cfg_path.exists(), f"alembic.ini missing at {cfg_path}"
    cfg = Config(str(cfg_path))
    # Override the URL — the env.py reads DATABASE_URL too, but the
    # programmatic path uses cfg.set_main_option().
    cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
    # Disarm the fileConfig() call inside env.py (see docstring above).
    cfg.config_file_name = None
    return cfg


@pytest.fixture
def db_path(tmp_path: Path) -> Generator[Path, None, None]:
    p = tmp_path / "zebu_l001_migration.db"
    yield p
    # tmp_path cleanup happens automatically.


def _has_table(engine: sa.Engine, table: str) -> bool:
    inspector = sa.inspect(engine)
    return inspector.has_table(table)


def _has_column(engine: sa.Engine, table: str, column: str) -> bool:
    inspector = sa.inspect(engine)
    if not inspector.has_table(table):
        return False
    return any(c["name"] == column for c in inspector.get_columns(table))


def _has_index(engine: sa.Engine, table: str, index_name: str) -> bool:
    inspector = sa.inspect(engine)
    if not inspector.has_table(table):
        return False
    return any(i["name"] == index_name for i in inspector.get_indexes(table))


class TestL001Migration:
    def test_upgrade_creates_table_column_and_indexes(self, db_path: Path) -> None:
        cfg = _alembic_cfg(db_path)
        # Tell env.py via DATABASE_URL too, in case it short-circuits.
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        try:
            upgrade(cfg, "head")
        finally:
            os.environ.pop("DATABASE_URL", None)

        engine = sa.create_engine(f"sqlite:///{db_path}")
        try:
            assert _has_table(engine, "backtest_agent_invocations"), (
                "backtest_agent_invocations table not created"
            )
            assert _has_column(engine, "backtest_runs", "agent_invocation_mode"), (
                "agent_invocation_mode column not added to backtest_runs"
            )
            assert _has_index(
                engine,
                "backtest_agent_invocations",
                "idx_bt_agent_invocation_run_date",
            )
            assert _has_index(
                engine,
                "backtest_agent_invocations",
                "idx_bt_agent_invocation_trigger",
            )
        finally:
            engine.dispose()

    def test_downgrade_reverses_table_and_column(self, db_path: Path) -> None:
        cfg = _alembic_cfg(db_path)
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        try:
            upgrade(cfg, "l001_backtest_agent_invocations")
            downgrade(cfg, "-1")
        finally:
            os.environ.pop("DATABASE_URL", None)

        engine = sa.create_engine(f"sqlite:///{db_path}")
        try:
            assert not _has_table(engine, "backtest_agent_invocations"), (
                "backtest_agent_invocations table not dropped by downgrade"
            )
            assert not _has_column(engine, "backtest_runs", "agent_invocation_mode"), (
                "agent_invocation_mode column not dropped from backtest_runs"
            )
        finally:
            engine.dispose()

    def test_idempotent_reupgrade(self, db_path: Path) -> None:
        cfg = _alembic_cfg(db_path)
        os.environ["DATABASE_URL"] = f"sqlite:///{db_path}"
        try:
            upgrade(cfg, "l001_backtest_agent_invocations")
            downgrade(cfg, "-1")
            upgrade(cfg, "l001_backtest_agent_invocations")
        finally:
            os.environ.pop("DATABASE_URL", None)

        engine = sa.create_engine(f"sqlite:///{db_path}")
        try:
            assert _has_table(engine, "backtest_agent_invocations")
            assert _has_column(engine, "backtest_runs", "agent_invocation_mode")
        finally:
            engine.dispose()
