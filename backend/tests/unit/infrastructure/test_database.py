from zebu.infrastructure.database import should_auto_create_schema


class TestShouldAutoCreateSchema:
    def test_sqlite_always_bootstraps(self) -> None:
        assert should_auto_create_schema(
            database_url="sqlite+aiosqlite:///./papertrade.db",
            db_auto_create=False,
            has_alembic_version_table=True,
        )

    def test_postgres_bootstraps_when_explicitly_enabled(self) -> None:
        assert should_auto_create_schema(
            database_url="postgresql+asyncpg://user:pass@db:5432/papertrade",
            db_auto_create=True,
            has_alembic_version_table=True,
        )

    def test_postgres_bootstraps_when_alembic_history_is_missing(self) -> None:
        assert should_auto_create_schema(
            database_url="postgresql+asyncpg://user:pass@db:5432/papertrade",
            db_auto_create=False,
            has_alembic_version_table=False,
        )

    def test_postgres_skips_create_all_when_alembic_history_exists(self) -> None:
        assert not should_auto_create_schema(
            database_url="postgresql+asyncpg://user:pass@db:5432/papertrade",
            db_auto_create=False,
            has_alembic_version_table=True,
        )
