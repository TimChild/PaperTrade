"""SQLModel database models for persistence.

These models represent the database schema and provide conversion functions
to/from domain entities.
"""

import logging
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import TypedDict
from uuid import UUID

from sqlmodel import JSON, Column, Field, Index, SQLModel, UniqueConstraint

from zebu.domain.entities.backfill_task import BackfillTask
from zebu.domain.entities.backtest_run import BacktestRun
from zebu.domain.entities.exploration_task import (
    ExplorationConstraints,
    ExplorationFindings,
    ExplorationFindingsComparison,
    ExplorationFindingsMetrics,
    ExplorationTask,
    ExplorationTaskStatus,
)
from zebu.domain.entities.portfolio import Portfolio
from zebu.domain.entities.portfolio_snapshot import (
    HoldingBreakdown,
    PortfolioSnapshot,
)
from zebu.domain.entities.strategy import Strategy
from zebu.domain.entities.strategy_activation import StrategyActivation
from zebu.domain.entities.strategy_condition_trigger import StrategyConditionTrigger
from zebu.domain.entities.transaction import Transaction, TransactionType
from zebu.domain.entities.trigger_fire_record import TriggerFireRecord
from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.activation_frequency import ActivationFrequency
from zebu.domain.value_objects.activation_status import ActivationStatus
from zebu.domain.value_objects.agent_decision import AgentDecision
from zebu.domain.value_objects.backfill_priority import BackfillPriority
from zebu.domain.value_objects.backfill_task_status import BackfillTaskStatus
from zebu.domain.value_objects.backtest_status import BacktestStatus
from zebu.domain.value_objects.job_execution import JobExecution
from zebu.domain.value_objects.job_execution_status import JobExecutionStatus
from zebu.domain.value_objects.money import Money
from zebu.domain.value_objects.portfolio_type import PortfolioType
from zebu.domain.value_objects.quantity import Quantity
from zebu.domain.value_objects.strategy_parameters import parameters_from_dict
from zebu.domain.value_objects.strategy_snapshot import StrategySnapshot
from zebu.domain.value_objects.strategy_type import StrategyType
from zebu.domain.value_objects.ticker import Ticker
from zebu.domain.value_objects.trigger_condition import (
    ConditionType,
    params_from_dict,
)
from zebu.domain.value_objects.trigger_status import TriggerStatus

_logger = logging.getLogger(__name__)


class HoldingBreakdownDict(TypedDict):
    """JSON-serializable representation of a HoldingBreakdown."""

    ticker: str
    quantity: int
    price_per_share: str
    value: str


class PortfolioModel(SQLModel, table=True):
    """Database model for Portfolio entity.

    Attributes:
        id: Primary key (UUID)
        user_id: Foreign key to user (UUID) - indexed for get_by_user queries
        name: Portfolio display name
        created_at: Timestamp of portfolio creation
        updated_at: Timestamp of last modification
        version: Version number for optimistic locking
    """

    __tablename__ = "portfolios"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (Index("idx_portfolio_user_id", "user_id"),)

    id: UUID = Field(primary_key=True)
    # NOTE: user_id intentionally has NO foreign key — users live in Clerk
    # (external auth provider), there is no `users` table in this schema.
    user_id: UUID = Field(index=True)
    name: str = Field(max_length=100)
    created_at: datetime
    updated_at: datetime
    version: int = Field(default=1)
    portfolio_type: str = Field(default="PAPER_TRADING")

    def to_domain(self) -> Portfolio:
        """Convert database model to domain entity.

        Returns:
            Portfolio domain entity
        """
        # Database stores naive UTC datetimes - add UTC timezone back
        created_at_utc = self.created_at.replace(tzinfo=UTC)

        return Portfolio(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            created_at=created_at_utc,
            portfolio_type=PortfolioType(self.portfolio_type),
        )

    @classmethod
    def from_domain(cls, portfolio: Portfolio) -> "PortfolioModel":
        """Convert domain entity to database model.

        Args:
            portfolio: Domain Portfolio entity

        Returns:
            PortfolioModel for database persistence
        """
        now = datetime.now(UTC)
        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        # Convert to UTC first if needed, then strip timezone
        if portfolio.created_at.tzinfo:
            created_at_naive = portfolio.created_at.astimezone(UTC).replace(tzinfo=None)
        else:
            # Assume naive datetimes are already UTC (per domain contract)
            created_at_naive = portfolio.created_at
        updated_at_naive = now.replace(tzinfo=None)

        return cls(
            id=portfolio.id,
            user_id=portfolio.user_id,
            name=portfolio.name,
            created_at=created_at_naive,
            updated_at=updated_at_naive,
            version=1,
            portfolio_type=portfolio.portfolio_type.value,
        )


class TransactionModel(SQLModel, table=True):
    """Database model for Transaction entity.

    Transactions are immutable and append-only. The model flattens value objects
    (Money, Ticker, Quantity) into primitive columns for database storage.

    Attributes:
        id: Primary key (UUID)
        portfolio_id: Foreign key to portfolio (UUID) - indexed
        transaction_type: Type of transaction (DEPOSIT, WITHDRAWAL, BUY, SELL)
        timestamp: When the transaction occurred
        cash_change_amount: Amount of cash change (Decimal)
        cash_change_currency: Currency code (e.g., "USD")
        ticker: Stock symbol (optional, only for BUY/SELL)
        quantity: Number of shares (optional, only for BUY/SELL)
        price_per_share_amount: Price per share (optional, only for BUY/SELL)
        price_per_share_currency: Currency for price (optional, only for BUY/SELL)
        notes: Optional transaction notes
        created_at: When record was inserted (for audit)
    """

    __tablename__ = "transactions"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (
        Index("idx_transaction_portfolio_id", "portfolio_id"),
        Index("idx_transaction_timestamp", "timestamp"),
        Index("idx_transaction_portfolio_timestamp", "portfolio_id", "timestamp"),
        # Phase F-5: per-trigger fire-log lookup. The simple index covers
        # ``WHERE trigger_id = ?`` joins from a TriggerFireRecord back to the
        # canonical transaction; the composite (trigger_id, created_at) backs
        # the activity feed's "latest trades by this trigger" query without a
        # sort step.
        Index("idx_transaction_trigger_id", "trigger_id"),
        Index(
            "idx_transaction_trigger_created_at",
            "trigger_id",
            "created_at",
        ),
    )

    id: UUID = Field(primary_key=True)
    # FK to portfolios.id with ON DELETE CASCADE — transactions are
    # owned by their portfolio and removed when the portfolio is deleted.
    portfolio_id: UUID = Field(
        index=True,
        foreign_key="portfolios.id",
        ondelete="CASCADE",
    )
    transaction_type: str = Field(max_length=20)
    timestamp: datetime
    cash_change_amount: Decimal = Field(max_digits=15, decimal_places=2)
    cash_change_currency: str = Field(max_length=3)
    ticker: str | None = Field(default=None, max_length=5)
    quantity: Decimal | None = Field(default=None, max_digits=15, decimal_places=4)
    price_per_share_amount: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=2
    )
    price_per_share_currency: str | None = Field(default=None, max_length=3)
    notes: str | None = Field(default=None, max_length=500)
    created_at: datetime = Field(default_factory=datetime.now)
    # Phase H2: stamps which API key (if any) authenticated the request that
    # wrote this row. Null for Clerk Bearer (human via UI). FK is ON DELETE
    # SET NULL — deleting an API key must not erase historical activity, just
    # detach the credential reference. The activity-feed aggregator joins on
    # this column to surface the API-key label as the actor identity.
    api_key_id: UUID | None = Field(
        default=None,
        foreign_key="api_keys.id",
        ondelete="SET NULL",
    )
    # Phase F-5: stamps the trigger fire that produced this transaction
    # (when the transaction was caused by a woken-agent BUY/SELL decision).
    # Null for trades that did NOT come from a trigger fire — direct
    # human-initiated trades, daily-strategy execution-loop trades, deposit
    # / withdrawal / adjust transactions. FK is ON DELETE SET NULL — the
    # trigger's lifecycle is independent of the trades it caused; deleting
    # a trigger should not erase historical trades.
    trigger_id: UUID | None = Field(
        default=None,
        foreign_key="strategy_condition_triggers.id",
        ondelete="SET NULL",
    )

    def to_domain(self) -> Transaction:
        """Convert database model to domain entity.

        Returns:
            Transaction domain entity with reconstructed value objects
        """
        # Reconstruct value objects from primitive fields
        cash_change = Money(self.cash_change_amount, self.cash_change_currency)

        ticker_obj: Ticker | None = None
        quantity_obj: Quantity | None = None
        price_obj: Money | None = None

        if self.ticker:
            ticker_obj = Ticker(self.ticker)
        if self.quantity is not None:
            quantity_obj = Quantity(self.quantity)
        if self.price_per_share_amount is not None and self.price_per_share_currency:
            price_obj = Money(
                self.price_per_share_amount, self.price_per_share_currency
            )

        # Database stores naive UTC datetimes - add UTC timezone back
        timestamp_utc = self.timestamp.replace(tzinfo=UTC)

        return Transaction(
            id=self.id,
            portfolio_id=self.portfolio_id,
            transaction_type=TransactionType[self.transaction_type],
            timestamp=timestamp_utc,
            cash_change=cash_change,
            ticker=ticker_obj,
            quantity=quantity_obj,
            price_per_share=price_obj,
            notes=self.notes,
        )

    @classmethod
    def from_domain(cls, transaction: Transaction) -> "TransactionModel":
        """Convert domain entity to database model.

        Args:
            transaction: Domain Transaction entity

        Returns:
            TransactionModel for database persistence
        """
        # Flatten value objects to primitive fields
        ticker_str: str | None = None
        quantity_dec: Decimal | None = None
        price_amount: Decimal | None = None
        price_currency: str | None = None

        if transaction.ticker:
            ticker_str = transaction.ticker.symbol
        if transaction.quantity:
            quantity_dec = transaction.quantity.shares
        if transaction.price_per_share:
            price_amount = transaction.price_per_share.amount
            price_currency = transaction.price_per_share.currency

        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        # Convert to UTC first if needed, then strip timezone
        now = datetime.now(UTC)
        created_at_naive = now.replace(tzinfo=None)

        if transaction.timestamp.tzinfo:
            timestamp_naive = transaction.timestamp.astimezone(UTC).replace(tzinfo=None)
        else:
            # Assume naive datetimes are already UTC (per domain contract)
            timestamp_naive = transaction.timestamp

        return cls(
            id=transaction.id,
            portfolio_id=transaction.portfolio_id,
            transaction_type=transaction.transaction_type.value,
            timestamp=timestamp_naive,
            cash_change_amount=transaction.cash_change.amount,
            cash_change_currency=transaction.cash_change.currency,
            ticker=ticker_str,
            quantity=quantity_dec,
            price_per_share_amount=price_amount,
            price_per_share_currency=price_currency,
            notes=transaction.notes,
            created_at=created_at_naive,
        )


class PortfolioSnapshotModel(SQLModel, table=True):
    """Database model for portfolio snapshots.

    Snapshots represent the daily state of a portfolio for analytics.
    One snapshot per portfolio per day (unique constraint enforced).

    Attributes:
        id: Primary key (UUID)
        portfolio_id: Foreign key to portfolio (UUID) - indexed
        snapshot_date: Date of snapshot (end-of-day)
        total_value: Total portfolio value (cash + holdings)
        cash_balance: Available cash
        holdings_value: Total value of all holdings
        holdings_count: Number of unique stocks held
        created_at: When snapshot was calculated
        holdings_breakdown: Per-holding value breakdown (JSON, nullable for old rows)
    """

    __tablename__ = "portfolio_snapshots"  # type: ignore[assignment]  # SQLModel requires string literal for __tablename__
    __table_args__ = (
        UniqueConstraint(
            "portfolio_id", "snapshot_date", name="uq_snapshot_portfolio_date"
        ),
        Index("idx_snapshot_portfolio_date", "portfolio_id", "snapshot_date"),
        Index("idx_snapshot_date", "snapshot_date"),
    )

    id: UUID = Field(primary_key=True)
    # FK to portfolios.id with ON DELETE CASCADE — snapshots are
    # owned by their portfolio and removed when the portfolio is deleted.
    portfolio_id: UUID = Field(
        index=False,  # Index covered by composite index
        foreign_key="portfolios.id",
        ondelete="CASCADE",
    )
    snapshot_date: date
    total_value: Decimal = Field(max_digits=15, decimal_places=2)
    cash_balance: Decimal = Field(max_digits=15, decimal_places=2)
    holdings_value: Decimal = Field(max_digits=15, decimal_places=2)
    holdings_count: int
    created_at: datetime
    holdings_breakdown: list[HoldingBreakdownDict] | None = Field(
        default=None,
        sa_column=Column(JSON, nullable=True),
    )

    def to_domain(self) -> PortfolioSnapshot:
        """Convert database model to domain entity.

        Returns:
            PortfolioSnapshot domain entity
        """
        # Database stores naive UTC datetimes - add UTC timezone back
        created_at_utc = self.created_at.replace(tzinfo=UTC)

        # Convert JSON dicts back to HoldingBreakdown domain objects
        breakdown: list[HoldingBreakdown] = []
        if self.holdings_breakdown:
            breakdown = [
                HoldingBreakdown(
                    ticker=item["ticker"],
                    quantity=item["quantity"],
                    price_per_share=Decimal(item["price_per_share"]),
                    value=Decimal(item["value"]),
                )
                for item in self.holdings_breakdown
            ]

        return PortfolioSnapshot(
            id=self.id,
            portfolio_id=self.portfolio_id,
            snapshot_date=self.snapshot_date,
            total_value=self.total_value,
            cash_balance=self.cash_balance,
            holdings_value=self.holdings_value,
            holdings_count=self.holdings_count,
            created_at=created_at_utc,
            holdings_breakdown=breakdown,
        )

    @classmethod
    def from_domain(cls, snapshot: PortfolioSnapshot) -> "PortfolioSnapshotModel":
        """Convert domain entity to database model.

        Args:
            snapshot: Domain PortfolioSnapshot entity

        Returns:
            PortfolioSnapshotModel for database persistence
        """
        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        if snapshot.created_at.tzinfo:
            created_at_naive = snapshot.created_at.astimezone(UTC).replace(tzinfo=None)
        else:
            # Assume naive datetimes are already UTC (per domain contract)
            created_at_naive = snapshot.created_at

        # Convert HoldingBreakdown domain objects to plain dicts for JSON storage
        breakdown_json: list[HoldingBreakdownDict] | None = None
        if snapshot.holdings_breakdown:
            breakdown_json = [
                {
                    "ticker": h.ticker,
                    "quantity": h.quantity,
                    "price_per_share": str(h.price_per_share),
                    "value": str(h.value),
                }
                for h in snapshot.holdings_breakdown
            ]

        return cls(
            id=snapshot.id,
            portfolio_id=snapshot.portfolio_id,
            snapshot_date=snapshot.snapshot_date,
            total_value=snapshot.total_value,
            cash_balance=snapshot.cash_balance,
            holdings_value=snapshot.holdings_value,
            holdings_count=snapshot.holdings_count,
            created_at=created_at_naive,
            holdings_breakdown=breakdown_json,
        )


class StrategyModel(SQLModel, table=True):
    """Database model for Strategy entity.

    Attributes:
        id: Primary key (UUID)
        user_id: Owner of the strategy - indexed for get_by_user queries
        name: Human-readable strategy name
        strategy_type: Algorithm type string (e.g. 'BUY_AND_HOLD')
        tickers: JSON array of ticker symbols
        parameters: JSON object of algorithm-specific configuration
        created_at: Timestamp of strategy creation
    """

    __tablename__ = "strategies"  # type: ignore[assignment]
    __table_args__ = (Index("idx_strategy_user_id", "user_id"),)

    id: UUID = Field(primary_key=True)
    # NOTE: user_id intentionally has NO foreign key — users live in Clerk
    # (external auth provider), there is no `users` table in this schema.
    user_id: UUID = Field(index=True)
    name: str = Field(max_length=100)
    strategy_type: str = Field(max_length=50)
    tickers: list[str] = Field(  # type: ignore[assignment]
        sa_column=Column(JSON, nullable=False)
    )
    parameters: dict[str, object] = Field(  # type: ignore[assignment]
        sa_column=Column(JSON, nullable=False)
    )
    created_at: datetime
    # Phase H2: see TransactionModel.api_key_id for the full doc. Null for
    # Clerk Bearer rows; activity-feed aggregator joins to api_keys.label.
    api_key_id: UUID | None = Field(
        default=None,
        foreign_key="api_keys.id",
        ondelete="SET NULL",
    )

    def to_domain(self) -> Strategy:
        """Convert database model to domain entity.

        Returns:
            Strategy domain entity
        """
        created_at_utc = self.created_at.replace(tzinfo=UTC)
        strategy_type = StrategyType(self.strategy_type)
        # Parse the JSON parameters back into the typed dataclass. Raises
        # InvalidStrategyError on shape drift (e.g. an old row with missing
        # fields) — the repository surfaces this loudly rather than
        # silently returning a half-typed entity.
        parameters = parameters_from_dict(strategy_type, dict(self.parameters))
        return Strategy(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            strategy_type=strategy_type,
            tickers=list(self.tickers),
            parameters=parameters,
            created_at=created_at_utc,
        )

    @classmethod
    def from_domain(cls, strategy: Strategy) -> "StrategyModel":
        """Convert domain entity to database model.

        Args:
            strategy: Domain Strategy entity

        Returns:
            StrategyModel for database persistence
        """
        if strategy.created_at.tzinfo:
            created_at_naive = strategy.created_at.astimezone(UTC).replace(tzinfo=None)
        else:
            created_at_naive = strategy.created_at

        return cls(
            id=strategy.id,
            user_id=strategy.user_id,
            name=strategy.name,
            strategy_type=strategy.strategy_type.value,
            tickers=strategy.tickers,
            parameters=dict(strategy.parameters.to_dict()),
            created_at=created_at_naive,
        )


class BacktestRunModel(SQLModel, table=True):
    """Database model for BacktestRun entity.

    Attributes:
        id: Primary key (UUID)
        user_id: Owner of the run - indexed
        strategy_id: Optional reference to the strategy entity
        portfolio_id: Portfolio created for this backtest
        strategy_snapshot: JSON copy of strategy config at run time
        backtest_name: Human-readable label
        start_date: Start of simulation window
        end_date: End of simulation window
        initial_cash: Starting cash balance in USD
        status: Lifecycle status string
        created_at: When the run was created
        completed_at: When the run finished (nullable)
        error_message: Failure reason (nullable)
        total_return_pct: Percentage return (nullable, set on completion)
        max_drawdown_pct: Maximum drawdown (nullable, set on completion)
        annualized_return_pct: Annualized return (nullable, set on completion)
        total_trades: Number of trades executed (nullable, set on completion)
    """

    __tablename__ = "backtest_runs"  # type: ignore[assignment]
    __table_args__ = (
        Index("idx_backtest_run_user_id", "user_id"),
        Index("idx_backtest_run_portfolio_id", "portfolio_id"),
        Index("idx_backtest_run_strategy_id", "strategy_id"),
    )

    id: UUID = Field(primary_key=True)
    # NOTE: user_id intentionally has NO foreign key — users live in Clerk
    # (external auth provider), there is no `users` table in this schema.
    user_id: UUID = Field(index=True)
    # FK to strategies.id with ON DELETE SET NULL — soft reference: a deleted
    # strategy must not erase backtest history; the run's strategy_snapshot
    # column already preserves the configuration that was used.
    strategy_id: UUID | None = Field(
        default=None,
        foreign_key="strategies.id",
        ondelete="SET NULL",
    )
    # FK to portfolios.id with ON DELETE CASCADE — every backtest run owns
    # its own (synthetic) portfolio; deleting that portfolio removes the run.
    portfolio_id: UUID = Field(
        index=True,
        foreign_key="portfolios.id",
        ondelete="CASCADE",
    )
    strategy_snapshot: dict[str, object] = Field(  # type: ignore[assignment]
        sa_column=Column(JSON, nullable=False)
    )
    backtest_name: str = Field(max_length=100)
    start_date: date
    end_date: date
    initial_cash: Decimal = Field(max_digits=15, decimal_places=2)
    status: str = Field(max_length=20)
    created_at: datetime
    completed_at: datetime | None = Field(default=None)
    error_message: str | None = Field(default=None, max_length=500)
    total_return_pct: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=4
    )
    max_drawdown_pct: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=4
    )
    annualized_return_pct: Decimal | None = Field(
        default=None, max_digits=15, decimal_places=4
    )
    total_trades: int | None = Field(default=None)
    # Phase H2: see TransactionModel.api_key_id for the full doc. Null for
    # Clerk Bearer rows; activity-feed aggregator joins to api_keys.label.
    api_key_id: UUID | None = Field(
        default=None,
        foreign_key="api_keys.id",
        ondelete="SET NULL",
    )

    def to_domain(self) -> BacktestRun:
        """Convert database model to domain entity.

        Returns:
            BacktestRun domain entity

        Raises:
            InvalidStrategyError: If the JSON ``strategy_snapshot`` cannot be
                parsed into a ``StrategySnapshot`` (unknown ``strategy_type``,
                missing ``parameters``, etc.). Old rows from before the
                typed-parameters refactor may have a slightly different
                shape and trigger this — the failure is loud rather than
                silent so the operator can decide whether to migrate.
        """
        created_at_utc = self.created_at.replace(tzinfo=UTC)
        completed_at_utc: datetime | None = None
        if self.completed_at is not None:
            completed_at_utc = self.completed_at.replace(tzinfo=UTC)

        try:
            snapshot = StrategySnapshot.from_dict(dict(self.strategy_snapshot))
        except InvalidStrategyError:
            _logger.exception(
                "Failed to parse strategy_snapshot for backtest_run %s; "
                "row may have been written before the typed-parameters "
                "refactor",
                self.id,
            )
            raise

        return BacktestRun(
            id=self.id,
            user_id=self.user_id,
            strategy_id=self.strategy_id,
            portfolio_id=self.portfolio_id,
            strategy_snapshot=snapshot,
            backtest_name=self.backtest_name,
            start_date=self.start_date,
            end_date=self.end_date,
            initial_cash=Money(self.initial_cash, "USD"),
            status=BacktestStatus(self.status),
            created_at=created_at_utc,
            completed_at=completed_at_utc,
            error_message=self.error_message,
            total_return_pct=self.total_return_pct,
            max_drawdown_pct=self.max_drawdown_pct,
            annualized_return_pct=self.annualized_return_pct,
            total_trades=self.total_trades,
        )

    @classmethod
    def from_domain(cls, backtest_run: BacktestRun) -> "BacktestRunModel":
        """Convert domain entity to database model.

        Args:
            backtest_run: Domain BacktestRun entity

        Returns:
            BacktestRunModel for database persistence
        """
        if backtest_run.created_at.tzinfo:
            created_at_naive = backtest_run.created_at.astimezone(UTC).replace(
                tzinfo=None
            )
        else:
            created_at_naive = backtest_run.created_at

        completed_at_naive: datetime | None = None
        if backtest_run.completed_at is not None:
            if backtest_run.completed_at.tzinfo:
                completed_at_naive = backtest_run.completed_at.astimezone(UTC).replace(
                    tzinfo=None
                )
            else:
                completed_at_naive = backtest_run.completed_at

        return cls(
            id=backtest_run.id,
            user_id=backtest_run.user_id,
            strategy_id=backtest_run.strategy_id,
            portfolio_id=backtest_run.portfolio_id,
            strategy_snapshot=dict(backtest_run.strategy_snapshot.to_dict()),
            backtest_name=backtest_run.backtest_name,
            start_date=backtest_run.start_date,
            end_date=backtest_run.end_date,
            initial_cash=backtest_run.initial_cash.amount,
            status=backtest_run.status.value,
            created_at=created_at_naive,
            completed_at=completed_at_naive,
            error_message=backtest_run.error_message,
            total_return_pct=backtest_run.total_return_pct,
            max_drawdown_pct=backtest_run.max_drawdown_pct,
            annualized_return_pct=backtest_run.annualized_return_pct,
            total_trades=backtest_run.total_trades,
        )


class StrategyActivationModel(SQLModel, table=True):
    """Database model for StrategyActivation entity.

    A StrategyActivation links a Strategy to a Portfolio for live execution.

    Foreign keys:

    - ``strategy_id`` -> ``strategies.id`` ON DELETE CASCADE — an activation
      has no purpose once its strategy is gone.
    - ``portfolio_id`` -> ``portfolios.id`` ON DELETE CASCADE — same: trade
      target gone, activation should disappear with it.

    The ``user_id`` column has NO foreign key. Users live in Clerk (external
    auth provider); there is no ``users`` table in this schema. This matches
    the convention set by Alembic ``d26cec7cdf69`` (PR #224).

    Attributes:
        id: Primary key (UUID).
        user_id: Owner of the activation. Indexed via the composite
            ``(user_id, status)`` index for ``list_for_user`` queries.
        strategy_id: FK to ``strategies.id``.
        portfolio_id: FK to ``portfolios.id``.
        status: Lifecycle status string (matches :class:`ActivationStatus`).
        frequency: Cadence string (matches :class:`ActivationFrequency`).
        last_executed_at: Timestamp of last execution attempt (nullable until
            first run).
        last_error: Failure reason when ``status='ERROR'`` (nullable).
        created_at: When the activation was first created.
        updated_at: When the activation was last mutated.
    """

    __tablename__ = "strategy_activations"  # type: ignore[assignment]
    __table_args__ = (
        # Composite index supports the most-common query
        # (``list_for_user`` filtered by status) without needing a sequential
        # scan over all activations.
        Index(
            "idx_strategy_activation_user_status",
            "user_id",
            "status",
        ),
        Index("idx_strategy_activation_strategy_id", "strategy_id"),
        Index("idx_strategy_activation_portfolio_id", "portfolio_id"),
    )

    id: UUID = Field(primary_key=True)
    # NOTE: user_id intentionally has NO foreign key — users live in Clerk
    # (external auth provider); there is no ``users`` table in this schema.
    user_id: UUID
    # FK to strategies.id with ON DELETE CASCADE — an activation has no
    # purpose without its strategy, so removing the strategy removes the
    # activation. The Alembic migration declares the same constraint.
    strategy_id: UUID = Field(
        foreign_key="strategies.id",
        ondelete="CASCADE",
    )
    # FK to portfolios.id with ON DELETE CASCADE — same rationale: no
    # trade target, no activation.
    portfolio_id: UUID = Field(
        foreign_key="portfolios.id",
        ondelete="CASCADE",
    )
    status: str = Field(max_length=20)
    frequency: str = Field(max_length=30)
    last_executed_at: datetime | None = Field(default=None)
    last_error: str | None = Field(default=None, max_length=500)
    created_at: datetime
    updated_at: datetime
    # Phase H2: see TransactionModel.api_key_id for the full doc. Null for
    # Clerk Bearer rows; activity-feed aggregator joins to api_keys.label.
    api_key_id: UUID | None = Field(
        default=None,
        foreign_key="api_keys.id",
        ondelete="SET NULL",
    )

    def to_domain(self) -> StrategyActivation:
        """Convert database model to domain entity.

        Returns:
            StrategyActivation domain entity with timezone-aware timestamps.

        Raises:
            InvalidStrategyActivationError: If a row's ``status`` /
                ``frequency`` value drifts from the enum (e.g. an
                older row referring to a removed status).
        """
        # Database stores naive UTC datetimes - add UTC timezone back.
        created_at_utc = self.created_at.replace(tzinfo=UTC)
        updated_at_utc = self.updated_at.replace(tzinfo=UTC)
        last_executed_at_utc: datetime | None = None
        if self.last_executed_at is not None:
            last_executed_at_utc = self.last_executed_at.replace(tzinfo=UTC)

        return StrategyActivation(
            id=self.id,
            user_id=self.user_id,
            strategy_id=self.strategy_id,
            portfolio_id=self.portfolio_id,
            status=ActivationStatus(self.status),
            frequency=ActivationFrequency(self.frequency),
            last_executed_at=last_executed_at_utc,
            last_error=self.last_error,
            created_at=created_at_utc,
            updated_at=updated_at_utc,
        )

    @classmethod
    def from_domain(cls, activation: StrategyActivation) -> "StrategyActivationModel":
        """Convert domain entity to database model.

        Args:
            activation: Domain StrategyActivation entity.

        Returns:
            StrategyActivationModel for database persistence with naive UTC
            timestamps (PostgreSQL ``TIMESTAMP WITHOUT TIME ZONE``).
        """
        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns.
        # Convert to UTC first if needed, then strip timezone.
        if activation.created_at.tzinfo:
            created_at_naive = activation.created_at.astimezone(UTC).replace(
                tzinfo=None
            )
        else:
            created_at_naive = activation.created_at

        if activation.updated_at.tzinfo:
            updated_at_naive = activation.updated_at.astimezone(UTC).replace(
                tzinfo=None
            )
        else:
            updated_at_naive = activation.updated_at

        last_executed_at_naive: datetime | None = None
        if activation.last_executed_at is not None:
            if activation.last_executed_at.tzinfo:
                last_executed_at_naive = activation.last_executed_at.astimezone(
                    UTC
                ).replace(tzinfo=None)
            else:
                last_executed_at_naive = activation.last_executed_at

        return cls(
            id=activation.id,
            user_id=activation.user_id,
            strategy_id=activation.strategy_id,
            portfolio_id=activation.portfolio_id,
            status=activation.status.value,
            frequency=activation.frequency.value,
            last_executed_at=last_executed_at_naive,
            last_error=activation.last_error,
            created_at=created_at_naive,
            updated_at=updated_at_naive,
        )


class ExplorationTaskConstraintsDict(TypedDict, total=False):
    """JSON-serializable form of ExplorationConstraints stored in `constraints`.

    All fields are optional (``total=False``) so a row with no constraints
    set serialises as ``{}``. ``strategy_type_whitelist`` is stored as a
    list of strategy-type string values; the to_domain conversion rebuilds
    ``StrategyType`` enum members.
    """

    max_backtests: int | None
    allow_live_activation: bool
    strategy_type_whitelist: list[str] | None


class ExplorationTaskMetricsDict(TypedDict, total=False):
    """JSON-serialisable form of ExplorationFindingsMetrics.

    Decimal values are stored as strings to keep the wire/DB shape exact —
    same convention as BacktestRun's metric columns.
    """

    total_return_pct: str
    sharpe_ratio: str | None
    max_drawdown_pct: str | None
    n_trades: int | None
    annualized_return_pct: str | None


class ExplorationTaskComparisonDict(TypedDict, total=False):
    """JSON-serialisable form of ExplorationFindingsComparison."""

    baseline_strategy_id: str
    baseline_total_return_pct: str
    delta_total_return_pct: str
    delta_sharpe: str | None


class ExplorationTaskFindingsDict(TypedDict, total=False):
    """JSON-serializable form of ExplorationFindings stored in `findings`.

    UUIDs are serialised as their canonical hex strings; the to_domain
    conversion rebuilds the UUID objects.

    Phase E2 added the structured-recommendation fields. All E2 keys are
    optional (``total=False``) so existing rows without them deserialise
    cleanly.
    """

    summary: str
    backtest_run_ids: list[str]
    strategy_ids: list[str]
    notes: list[str] | None
    recommended_strategy_id: str | None
    # `recommended_parameters` is an opaque per-strategy-type JSON object;
    # we don't model it further here. Strategy-side typing happens in the
    # `strategy_parameters` value-object module.
    recommended_parameters: dict[str, object] | None
    metrics: ExplorationTaskMetricsDict | None
    comparison_to_baseline: ExplorationTaskComparisonDict | None
    confidence: float | None


def _constraints_to_dict(
    constraints: ExplorationConstraints | None,
) -> ExplorationTaskConstraintsDict | None:
    """Serialise ExplorationConstraints to a JSON dict (or None)."""
    if constraints is None:
        return None
    payload: ExplorationTaskConstraintsDict = {
        "max_backtests": constraints.max_backtests,
        "allow_live_activation": constraints.allow_live_activation,
        "strategy_type_whitelist": (
            [t.value for t in constraints.strategy_type_whitelist]
            if constraints.strategy_type_whitelist is not None
            else None
        ),
    }
    return payload


def _constraints_from_dict(
    raw: ExplorationTaskConstraintsDict | None,
) -> ExplorationConstraints | None:
    """Deserialise a JSON dict into ExplorationConstraints (or None)."""
    if raw is None:
        return None
    whitelist_raw = raw.get("strategy_type_whitelist")
    whitelist: list[StrategyType] | None
    if whitelist_raw is None:
        whitelist = None
    else:
        whitelist = [StrategyType(value) for value in whitelist_raw]
    return ExplorationConstraints(
        max_backtests=raw.get("max_backtests"),
        allow_live_activation=raw.get("allow_live_activation", True),
        strategy_type_whitelist=whitelist,
    )


def _metrics_to_dict(
    metrics: ExplorationFindingsMetrics | None,
) -> ExplorationTaskMetricsDict | None:
    """Serialise ExplorationFindingsMetrics to a JSON dict (or None)."""
    if metrics is None:
        return None
    payload: ExplorationTaskMetricsDict = {
        "total_return_pct": str(metrics.total_return_pct),
        "sharpe_ratio": (
            str(metrics.sharpe_ratio) if metrics.sharpe_ratio is not None else None
        ),
        "max_drawdown_pct": (
            str(metrics.max_drawdown_pct)
            if metrics.max_drawdown_pct is not None
            else None
        ),
        "n_trades": metrics.n_trades,
        "annualized_return_pct": (
            str(metrics.annualized_return_pct)
            if metrics.annualized_return_pct is not None
            else None
        ),
    }
    return payload


def _metrics_from_dict(
    raw: ExplorationTaskMetricsDict | None,
) -> ExplorationFindingsMetrics | None:
    """Deserialise a JSON dict into ExplorationFindingsMetrics (or None)."""
    if raw is None:
        return None
    total_return_raw = raw.get("total_return_pct")
    if total_return_raw is None:
        raise ValueError(
            "ExplorationFindings.metrics JSON missing required 'total_return_pct' field"
        )
    sharpe_raw = raw.get("sharpe_ratio")
    drawdown_raw = raw.get("max_drawdown_pct")
    annualized_raw = raw.get("annualized_return_pct")
    return ExplorationFindingsMetrics(
        total_return_pct=Decimal(total_return_raw),
        sharpe_ratio=Decimal(sharpe_raw) if sharpe_raw is not None else None,
        max_drawdown_pct=Decimal(drawdown_raw) if drawdown_raw is not None else None,
        n_trades=raw.get("n_trades"),
        annualized_return_pct=(
            Decimal(annualized_raw) if annualized_raw is not None else None
        ),
    )


def _comparison_to_dict(
    comparison: ExplorationFindingsComparison | None,
) -> ExplorationTaskComparisonDict | None:
    """Serialise ExplorationFindingsComparison to a JSON dict (or None)."""
    if comparison is None:
        return None
    payload: ExplorationTaskComparisonDict = {
        "baseline_strategy_id": str(comparison.baseline_strategy_id),
        "baseline_total_return_pct": str(comparison.baseline_total_return_pct),
        "delta_total_return_pct": str(comparison.delta_total_return_pct),
        "delta_sharpe": (
            str(comparison.delta_sharpe)
            if comparison.delta_sharpe is not None
            else None
        ),
    }
    return payload


def _comparison_from_dict(
    raw: ExplorationTaskComparisonDict | None,
) -> ExplorationFindingsComparison | None:
    """Deserialise a JSON dict into ExplorationFindingsComparison (or None)."""
    if raw is None:
        return None
    baseline_id_raw = raw.get("baseline_strategy_id")
    baseline_return_raw = raw.get("baseline_total_return_pct")
    delta_return_raw = raw.get("delta_total_return_pct")
    if (
        baseline_id_raw is None
        or baseline_return_raw is None
        or delta_return_raw is None
    ):
        raise ValueError(
            "ExplorationFindings.comparison_to_baseline JSON missing one of: "
            "baseline_strategy_id, baseline_total_return_pct, "
            "delta_total_return_pct"
        )
    delta_sharpe_raw = raw.get("delta_sharpe")
    return ExplorationFindingsComparison(
        baseline_strategy_id=UUID(baseline_id_raw),
        baseline_total_return_pct=Decimal(baseline_return_raw),
        delta_total_return_pct=Decimal(delta_return_raw),
        delta_sharpe=(
            Decimal(delta_sharpe_raw) if delta_sharpe_raw is not None else None
        ),
    )


def _findings_to_dict(
    findings: ExplorationFindings | None,
) -> ExplorationTaskFindingsDict | None:
    """Serialise ExplorationFindings to a JSON dict (or None).

    Phase E2 — emits the new structured fields when present. Existing
    rows without the new keys deserialise cleanly because every E2 key
    is optional in the entity.
    """
    if findings is None:
        return None
    payload: ExplorationTaskFindingsDict = {
        "summary": findings.summary,
        "backtest_run_ids": [str(run_id) for run_id in findings.backtest_run_ids],
        "strategy_ids": [str(s_id) for s_id in findings.strategy_ids],
        "notes": findings.notes,
        "recommended_strategy_id": (
            str(findings.recommended_strategy_id)
            if findings.recommended_strategy_id is not None
            else None
        ),
        # `recommended_parameters` is opaque JSON — pass through unchanged.
        "recommended_parameters": findings.recommended_parameters,
        "metrics": _metrics_to_dict(findings.metrics),
        "comparison_to_baseline": _comparison_to_dict(findings.comparison_to_baseline),
        "confidence": findings.confidence,
    }
    return payload


def _findings_from_dict(
    raw: ExplorationTaskFindingsDict | None,
) -> ExplorationFindings | None:
    """Deserialise a JSON dict into ExplorationFindings (or None).

    Backward-compatible: rows persisted before Phase E2 will not contain
    the new keys, and ``raw.get`` returns ``None`` for each, so the
    entity is constructed with ``None`` defaults — preserving the v1
    behaviour for existing data.
    """
    if raw is None:
        return None
    summary = raw.get("summary")
    if summary is None:
        # Defensive — should not happen since summary is required, but a
        # missing field shouldn't crash the loader silently.
        raise ValueError(
            "ExplorationTask.findings JSON missing required 'summary' field"
        )
    backtest_run_ids = [UUID(value) for value in raw.get("backtest_run_ids", [])]
    strategy_ids = [UUID(value) for value in raw.get("strategy_ids", [])]
    notes = raw.get("notes")
    recommended_strategy_id_raw = raw.get("recommended_strategy_id")
    recommended_strategy_id = (
        UUID(recommended_strategy_id_raw)
        if recommended_strategy_id_raw is not None
        else None
    )
    recommended_parameters = raw.get("recommended_parameters")
    return ExplorationFindings(
        summary=summary,
        backtest_run_ids=backtest_run_ids,
        strategy_ids=strategy_ids,
        notes=notes,
        recommended_strategy_id=recommended_strategy_id,
        recommended_parameters=recommended_parameters,
        metrics=_metrics_from_dict(raw.get("metrics")),
        comparison_to_baseline=_comparison_from_dict(raw.get("comparison_to_baseline")),
        confidence=raw.get("confidence"),
    )


class ExplorationTaskModel(SQLModel, table=True):
    """Database model for ExplorationTask entity.

    Tasks are the agent-platform queue: humans create them, agents claim
    them atomically, work them, submit findings. The composite index on
    ``(status, created_at)`` makes the "next OPEN task" query the queue is
    built around fast even at large row counts.

    Foreign-key behaviour:

    * ``target_portfolio_id`` references ``portfolios.id`` with ``ON DELETE
      SET NULL``: if a portfolio is deleted while a task referencing it is
      still open, the task survives but loses its portfolio binding. The
      FK constraint is declared in the Alembic migration.
    * ``created_by`` deliberately has **no FK** — users live in Clerk; this
      column matches the convention already used for ``portfolios.user_id``,
      ``strategies.user_id``, and ``backtest_runs.user_id``.

    Attributes:
        id: Primary key (UUID).
        created_by: ID of the user (Clerk-derived UUID) who created the
            task.
        prompt: Free-form prompt text (max 4000 characters at the domain
            level; the column allows longer for future-proofing).
        status: ExplorationTaskStatus value (string).
        target_portfolio_id: Optional portfolio reference (FK, SET NULL on
            delete).
        tickers: JSON array of ticker symbol strings, ``None`` if no ticker
            scope.
        constraints: JSON object form of ExplorationConstraints, ``None``
            if no constraints.
        claimed_by: Free-form agent identifier set when the task is
            claimed.
        claimed_at: Timestamp the task was claimed (naive UTC for
            Postgres TIMESTAMP).
        findings: JSON object form of ExplorationFindings, populated when
            the task transitions to DONE.
        created_at: Creation timestamp (naive UTC).
        updated_at: Last-transition timestamp (naive UTC).
    """

    __tablename__ = "exploration_tasks"  # type: ignore[assignment]
    __table_args__ = (
        Index("idx_exploration_task_status_created", "status", "created_at"),
        Index("idx_exploration_task_created_by", "created_by"),
        Index("idx_exploration_task_portfolio_id", "target_portfolio_id"),
    )

    id: UUID = Field(primary_key=True)
    created_by: UUID = Field(index=False)  # Index supplied by composite above
    prompt: str = Field(max_length=4000)
    status: str = Field(max_length=20)
    target_portfolio_id: UUID | None = Field(default=None)
    tickers: list[str] | None = Field(  # type: ignore[assignment]
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    constraints: ExplorationTaskConstraintsDict | None = Field(  # type: ignore[assignment]
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    claimed_by: str | None = Field(default=None, max_length=200)
    claimed_at: datetime | None = Field(default=None)
    findings: ExplorationTaskFindingsDict | None = Field(  # type: ignore[assignment]
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    created_at: datetime
    updated_at: datetime
    # Phase H2: see TransactionModel.api_key_id for the full doc. Null for
    # Clerk Bearer rows; activity-feed aggregator joins to api_keys.label.
    api_key_id: UUID | None = Field(
        default=None,
        foreign_key="api_keys.id",
        ondelete="SET NULL",
    )

    def to_domain(self) -> ExplorationTask:
        """Convert database model to domain entity.

        Raises:
            ValueError: If the row's ``status`` is not a valid
                ``ExplorationTaskStatus`` value or its ``findings`` JSON is
                shape-broken (e.g. missing required ``summary``).
        """
        # Database stores naive UTC datetimes - add UTC timezone back
        created_at_utc = self.created_at.replace(tzinfo=UTC)
        updated_at_utc = self.updated_at.replace(tzinfo=UTC)
        claimed_at_utc: datetime | None = None
        if self.claimed_at is not None:
            claimed_at_utc = self.claimed_at.replace(tzinfo=UTC)

        tickers: list[Ticker] | None
        if self.tickers is None:
            tickers = None
        else:
            tickers = [Ticker(symbol) for symbol in self.tickers]

        return ExplorationTask(
            id=self.id,
            created_by=self.created_by,
            prompt=self.prompt,
            status=ExplorationTaskStatus(self.status),
            created_at=created_at_utc,
            updated_at=updated_at_utc,
            target_portfolio_id=self.target_portfolio_id,
            tickers=tickers,
            constraints=_constraints_from_dict(self.constraints),
            claimed_by=self.claimed_by,
            claimed_at=claimed_at_utc,
            findings=_findings_from_dict(self.findings),
        )

    @classmethod
    def from_domain(cls, task: ExplorationTask) -> "ExplorationTaskModel":
        """Convert domain entity to database model."""
        # Strip timezone for PostgreSQL TIMESTAMP WITHOUT TIME ZONE columns
        if task.created_at.tzinfo:
            created_at_naive = task.created_at.astimezone(UTC).replace(tzinfo=None)
        else:
            created_at_naive = task.created_at

        if task.updated_at.tzinfo:
            updated_at_naive = task.updated_at.astimezone(UTC).replace(tzinfo=None)
        else:
            updated_at_naive = task.updated_at

        claimed_at_naive: datetime | None = None
        if task.claimed_at is not None:
            if task.claimed_at.tzinfo:
                claimed_at_naive = task.claimed_at.astimezone(UTC).replace(tzinfo=None)
            else:
                claimed_at_naive = task.claimed_at

        tickers_json: list[str] | None
        if task.tickers is None:
            tickers_json = None
        else:
            tickers_json = [t.symbol for t in task.tickers]

        return cls(
            id=task.id,
            created_by=task.created_by,
            prompt=task.prompt,
            status=task.status.value,
            target_portfolio_id=task.target_portfolio_id,
            tickers=tickers_json,
            constraints=_constraints_to_dict(task.constraints),
            claimed_by=task.claimed_by,
            claimed_at=claimed_at_naive,
            findings=_findings_to_dict(task.findings),
            created_at=created_at_naive,
            updated_at=updated_at_naive,
        )


def _strip_tz(value: datetime | None) -> datetime | None:
    """Strip timezone from a datetime for naive PostgreSQL columns.

    Mirrors the per-model helpers above; broken out so the trigger
    models can share it. Returns ``None`` unchanged.
    """
    if value is None:
        return None
    if value.tzinfo is None:
        return value
    return value.astimezone(UTC).replace(tzinfo=None)


def _attach_utc(value: datetime | None) -> datetime | None:
    """Reattach UTC tzinfo to a naive datetime read from the DB.

    Mirrors the inline ``replace(tzinfo=UTC)`` calls used elsewhere in
    this module — broken out for the trigger models since they have
    several nullable timestamp fields.
    """
    if value is None:
        return None
    return value.replace(tzinfo=UTC)


class StrategyConditionTriggerModel(SQLModel, table=True):
    """Database model for :class:`StrategyConditionTrigger` (Phase F-1).

    A trigger attaches to exactly one ``StrategyActivation``. Each
    scheduler tick the evaluator (Phase F-2) walks evaluable triggers,
    checks the condition, and on fire invokes the Anthropic agent.

    Foreign keys:

    * ``activation_id`` -> ``strategy_activations.id`` ON DELETE CASCADE
      — a trigger has no purpose once its activation is gone.
    * ``default_api_key_id`` -> ``api_keys.id`` ON DELETE SET NULL — the
      key the woken agent should act under; revoking the key must not
      erase the trigger configuration. The fallback path described in
      the Phase F design §4.1 takes over when the column is null.

    The ``user_id`` column has NO foreign key (users live in Clerk).

    The ``condition_params`` column is a JSONB-style JSON column. The
    domain-side discriminated union (:mod:`zebu.domain.value_objects.trigger_condition`)
    rebuilds the typed VO via :func:`params_from_dict`.

    Indexes:

    * ``(activation_id, status)`` — fast trigger lookup per activation
      (frontend trigger-list view + per-activation evaluator scan).
    * ``(status, last_fired_at)`` — evaluator scan: filters
      ``status='ACTIVE'`` then orders by ``last_fired_at`` to surface
      cooldown-expired triggers first. Helps the (priority DESC,
      created_at ASC) sort path used by ``list_evaluable``.
    * ``(user_id, status)`` — backs ``list_for_user`` (the dashboard's
      "my triggers" view).

    Attributes:
        id: Primary key (UUID).
        activation_id: FK to ``strategy_activations.id``.
        user_id: Owner UUID (no FK — Clerk-managed).
        condition_type: Discriminator string (matches
            :class:`ConditionType`).
        condition_params: JSON object form of the typed condition VO.
            Stored as ``dict[str, object]`` for SQLAlchemy / SQLite
            compatibility; the domain reconstructs the typed VO via
            :func:`params_from_dict`.
        agent_prompt: Free-form trigger-fire instruction (10–4000 chars).
        cooldown_seconds: Minimum seconds between successive fires.
        last_fired_at: Last fire timestamp (naive UTC, nullable).
        status: :class:`TriggerStatus` value (string).
        priority: Integer in [-100, 100]; tiebreaker for evaluation order.
        default_api_key_id: FK to ``api_keys.id`` (nullable, SET NULL).
        expires_at: Natural expiry timestamp (naive UTC, nullable).
        created_at: Creation timestamp (naive UTC).
        created_by: User / API-key-derived UUID that created the trigger.
        updated_at: Last-mutation timestamp (naive UTC).
    """

    __tablename__ = "strategy_condition_triggers"  # type: ignore[assignment]
    __table_args__ = (
        Index(
            "idx_trigger_activation_status",
            "activation_id",
            "status",
        ),
        Index(
            "idx_trigger_status_last_fired",
            "status",
            "last_fired_at",
        ),
        Index(
            "idx_trigger_user_status",
            "user_id",
            "status",
        ),
    )

    id: UUID = Field(primary_key=True)
    # FK to strategy_activations.id with ON DELETE CASCADE — a trigger has
    # no purpose without its activation.
    activation_id: UUID = Field(
        foreign_key="strategy_activations.id",
        ondelete="CASCADE",
    )
    # NOTE: user_id intentionally has NO foreign key — users live in Clerk.
    user_id: UUID
    condition_type: str = Field(max_length=40)
    # JSON column for the discriminated-union condition params. Pyright's
    # strict mode flags the SQLModel + JSON pattern; the # type: ignore
    # mirrors the existing ``tickers`` / ``parameters`` columns elsewhere
    # in this module.
    condition_params: dict[str, object] = Field(  # type: ignore[assignment]
        sa_column=Column(JSON, nullable=False)
    )
    agent_prompt: str = Field(max_length=4000)
    cooldown_seconds: int = Field(default=21600)
    last_fired_at: datetime | None = Field(default=None)
    status: str = Field(max_length=30)
    priority: int = Field(default=0)
    # FK to api_keys.id with ON DELETE SET NULL — revoking the key must
    # not delete the trigger; the fallback path resolves to the user's
    # most-recently-used trade-scoped key.
    default_api_key_id: UUID | None = Field(
        default=None,
        foreign_key="api_keys.id",
        ondelete="SET NULL",
    )
    expires_at: datetime | None = Field(default=None)
    created_at: datetime
    created_by: UUID
    updated_at: datetime

    def to_domain(self) -> StrategyConditionTrigger:
        """Convert database model to domain entity.

        Raises:
            InvalidTriggerError: If a stored ``condition_type`` /
                ``status`` value drifts from the enum, or
                ``condition_params`` JSON cannot be reconstructed into
                the typed VO.
        """
        # Reattach UTC tzinfo to the naive timestamps.
        created_at_utc = self.created_at.replace(tzinfo=UTC)
        updated_at_utc = self.updated_at.replace(tzinfo=UTC)
        last_fired_at_utc = _attach_utc(self.last_fired_at)
        expires_at_utc = _attach_utc(self.expires_at)

        condition_type = ConditionType(self.condition_type)
        # Defensive copy — entity __post_init__ rebinds anyway, but a
        # fresh dict insulates the domain from any in-place mutation
        # before the entity sees it.
        condition_params = params_from_dict(condition_type, dict(self.condition_params))
        status = TriggerStatus(self.status)

        return StrategyConditionTrigger(
            id=self.id,
            activation_id=self.activation_id,
            user_id=self.user_id,
            condition_type=condition_type,
            condition_params=condition_params,
            agent_prompt=self.agent_prompt,
            cooldown_seconds=self.cooldown_seconds,
            last_fired_at=last_fired_at_utc,
            status=status,
            priority=self.priority,
            default_api_key_id=self.default_api_key_id,
            expires_at=expires_at_utc,
            created_at=created_at_utc,
            created_by=self.created_by,
            updated_at=updated_at_utc,
        )

    @classmethod
    def from_domain(
        cls, trigger: StrategyConditionTrigger
    ) -> "StrategyConditionTriggerModel":
        """Convert domain entity to database model."""
        return cls(
            id=trigger.id,
            activation_id=trigger.activation_id,
            user_id=trigger.user_id,
            condition_type=trigger.condition_type.value,
            condition_params=dict(trigger.condition_params.to_dict()),
            agent_prompt=trigger.agent_prompt,
            cooldown_seconds=trigger.cooldown_seconds,
            last_fired_at=_strip_tz(trigger.last_fired_at),
            status=trigger.status.value,
            priority=trigger.priority,
            default_api_key_id=trigger.default_api_key_id,
            expires_at=_strip_tz(trigger.expires_at),
            created_at=_strip_tz(trigger.created_at) or trigger.created_at,
            created_by=trigger.created_by,
            updated_at=_strip_tz(trigger.updated_at) or trigger.updated_at,
        )


class TriggerFireRecordModel(SQLModel, table=True):
    """Database model for :class:`TriggerFireRecord` (Phase F-1).

    Append-only audit row. One row per trigger fire; no update / delete
    paths exposed by the repository.

    Foreign keys:

    * ``trigger_id`` -> ``strategy_condition_triggers.id`` ON DELETE
      CASCADE — fires belong to their trigger.
    * ``activation_id`` -> ``strategy_activations.id`` ON DELETE CASCADE
      — denormalised join column; cascades together with
      ``activation -> trigger -> fire``.
    * ``resulting_trade_id`` -> ``transactions.id`` ON DELETE SET NULL —
      a deleted transaction must not erase the audit row.
    * ``resulting_exploration_task_id`` -> ``exploration_tasks.id`` ON
      DELETE SET NULL — same rationale.
    * ``api_key_id_used`` -> ``api_keys.id`` ON DELETE RESTRICT — never
      lose attribution. A key with fire history can't be hard-deleted;
      callers must revoke (which leaves the row with ``revoked_at``
      set) instead.

    Indexes:

    * ``(trigger_id, fired_at)`` — backs ``list_for_trigger``.
    * ``(activation_id, fired_at)`` — backs ``list_for_activation``.

    Attributes:
        id: Primary key (UUID).
        trigger_id: FK to ``strategy_condition_triggers.id``.
        activation_id: FK to ``strategy_activations.id`` (denormalised).
        fired_at: When the evaluator decided to fire (naive UTC).
        condition_evaluation_data: JSON snapshot of the inputs that made
            the condition fire. Schema is per-condition-type; the
            ``schema_version`` field is part of every payload.
        agent_invocation_id: Anthropic message ID (nullable, ≤200 chars).
        agent_response: :class:`AgentDecision` value (string).
        agent_response_raw: Truncated free-text response (≤8000 chars).
        resulting_trade_id: FK to ``transactions.id`` (nullable).
        resulting_modify_payload: JSON object for MODIFY_STRATEGY
            (nullable).
        resulting_exploration_task_id: FK to ``exploration_tasks.id``
            (nullable).
        latency_ms: End-to-end latency in milliseconds.
        api_key_id_used: FK to ``api_keys.id`` (NOT NULL, RESTRICT).
    """

    __tablename__ = "trigger_fire_records"  # type: ignore[assignment]
    __table_args__ = (
        Index(
            "idx_trigger_fire_trigger_fired_at",
            "trigger_id",
            "fired_at",
        ),
        Index(
            "idx_trigger_fire_activation_fired_at",
            "activation_id",
            "fired_at",
        ),
    )

    id: UUID = Field(primary_key=True)
    # FK to strategy_condition_triggers.id with ON DELETE CASCADE —
    # fires belong to their trigger.
    trigger_id: UUID = Field(
        foreign_key="strategy_condition_triggers.id",
        ondelete="CASCADE",
    )
    # FK to strategy_activations.id with ON DELETE CASCADE — denormalised
    # for fast filtering by activation.
    activation_id: UUID = Field(
        foreign_key="strategy_activations.id",
        ondelete="CASCADE",
    )
    fired_at: datetime
    condition_evaluation_data: dict[str, object] = Field(  # type: ignore[assignment]
        sa_column=Column(JSON, nullable=False)
    )
    agent_invocation_id: str | None = Field(default=None, max_length=200)
    agent_response: str = Field(max_length=30)
    agent_response_raw: str = Field(max_length=8000)
    # FK to transactions.id with ON DELETE SET NULL — deleted transaction
    # must not erase the audit row.
    resulting_trade_id: UUID | None = Field(
        default=None,
        foreign_key="transactions.id",
        ondelete="SET NULL",
    )
    resulting_modify_payload: dict[str, object] | None = Field(  # type: ignore[assignment]
        default=None,
        sa_column=Column(JSON, nullable=True),
    )
    # FK to exploration_tasks.id with ON DELETE SET NULL — same rationale.
    resulting_exploration_task_id: UUID | None = Field(
        default=None,
        foreign_key="exploration_tasks.id",
        ondelete="SET NULL",
    )
    latency_ms: int
    # FK to api_keys.id with ON DELETE RESTRICT — never lose attribution.
    api_key_id_used: UUID = Field(
        foreign_key="api_keys.id",
        ondelete="RESTRICT",
    )

    def to_domain(self) -> TriggerFireRecord:
        """Convert database model to domain entity.

        Raises:
            ValueError: If ``agent_response`` drifts from
                :class:`AgentDecision`.
        """
        fired_at_utc = self.fired_at.replace(tzinfo=UTC)
        agent_response = AgentDecision(self.agent_response)

        # Defensive copies of the JSON columns insulate the domain from
        # any in-place mutation before the entity sees them.
        evaluation_data = dict(self.condition_evaluation_data)
        modify_payload: dict[str, object] | None
        if self.resulting_modify_payload is None:
            modify_payload = None
        else:
            modify_payload = dict(self.resulting_modify_payload)

        return TriggerFireRecord(
            id=self.id,
            trigger_id=self.trigger_id,
            activation_id=self.activation_id,
            fired_at=fired_at_utc,
            condition_evaluation_data=evaluation_data,
            agent_invocation_id=self.agent_invocation_id,
            agent_response=agent_response,
            agent_response_raw=self.agent_response_raw,
            resulting_trade_id=self.resulting_trade_id,
            resulting_modify_payload=modify_payload,
            resulting_exploration_task_id=self.resulting_exploration_task_id,
            latency_ms=self.latency_ms,
            api_key_id_used=self.api_key_id_used,
        )

    @classmethod
    def from_domain(cls, record: TriggerFireRecord) -> "TriggerFireRecordModel":
        """Convert domain entity to database model."""
        # condition_evaluation_data and resulting_modify_payload are
        # JSON columns — wrap in dict() to materialise the Mapping into
        # something SQLAlchemy can serialise.
        modify_payload: dict[str, object] | None
        if record.resulting_modify_payload is None:
            modify_payload = None
        else:
            modify_payload = dict(record.resulting_modify_payload)

        return cls(
            id=record.id,
            trigger_id=record.trigger_id,
            activation_id=record.activation_id,
            fired_at=_strip_tz(record.fired_at) or record.fired_at,
            condition_evaluation_data=dict(record.condition_evaluation_data),
            agent_invocation_id=record.agent_invocation_id,
            agent_response=record.agent_response.value,
            agent_response_raw=record.agent_response_raw,
            resulting_trade_id=record.resulting_trade_id,
            resulting_modify_payload=modify_payload,
            resulting_exploration_task_id=record.resulting_exploration_task_id,
            latency_ms=record.latency_ms,
            api_key_id_used=record.api_key_id_used,
        )


class JobExecutionModel(SQLModel, table=True):
    """Database model for :class:`JobExecution` (Phase J — Task #212 Layer 1).

    Append-only-ish audit row for scheduled-job invocations. Rows are
    inserted in ``RUNNING`` state by ``@with_job_audit`` and updated in
    place to ``SUCCEEDED`` / ``FAILED`` at the end of the run. There is
    no delete path — operators reason about history; the per-job
    ``latest`` lookup is the hot path.

    The ``metadata`` column is a JSON object of ``str -> str``. Per-job
    schemas (e.g. ``{"duration_seconds": "47"}``,
    ``{"tickers_refreshed": "12"}``) are treated as opaque here — the
    domain entity does the same.

    Indexes:

    * ``(job_name, started_at DESC)`` — backs the per-job ``latest``
      lookup the health endpoint uses on every call.

    Attributes:
        id: Primary key (UUID).
        job_name: Stable scheduler-handler name (≤ 100 chars).
        started_at: Naive UTC timestamp when ``record_start`` ran.
        finished_at: Naive UTC timestamp when ``record_finish`` ran;
            ``None`` while ``status=RUNNING``.
        status: Lifecycle stage as a string (mirrors
            :class:`JobExecutionStatus`).
        error_message: Truncated exception message (≤ 500 chars) for
            ``FAILED`` rows.
        metadata_json: JSON payload — column name avoids the SQLModel
            ``metadata`` keyword conflict; the domain field name is
            ``metadata``.
    """

    __tablename__ = "job_executions"  # type: ignore[assignment]
    __table_args__ = (
        Index(
            "idx_job_executions_job_name_started_at",
            "job_name",
            "started_at",
        ),
    )

    id: UUID = Field(primary_key=True)
    job_name: str = Field(max_length=100, index=True)
    started_at: datetime
    finished_at: datetime | None = Field(default=None)
    status: str = Field(max_length=30)
    error_message: str | None = Field(default=None, max_length=500)
    metadata_json: dict[str, str] = Field(  # type: ignore[assignment]
        sa_column=Column("metadata", JSON, nullable=False),
    )

    def to_domain(self) -> JobExecution:
        """Convert database model to domain entity.

        Raises:
            ValueError: If ``status`` drifts from :class:`JobExecutionStatus`.
        """
        started_at_utc = self.started_at.replace(tzinfo=UTC)
        finished_at_utc = (
            self.finished_at.replace(tzinfo=UTC)
            if self.finished_at is not None
            else None
        )
        status = JobExecutionStatus(self.status)

        # Defensive copy of the JSON column.
        metadata_copy: dict[str, str] = {
            str(k): str(v) for k, v in self.metadata_json.items()
        }

        return JobExecution(
            id=self.id,
            job_name=self.job_name,
            started_at=started_at_utc,
            finished_at=finished_at_utc,
            status=status,
            error_message=self.error_message,
            metadata=metadata_copy,
        )

    @classmethod
    def from_domain(cls, execution: JobExecution) -> "JobExecutionModel":
        """Convert domain entity to database model."""
        started_at_naive = _strip_tz(execution.started_at) or execution.started_at
        finished_at_naive = _strip_tz(execution.finished_at)

        # Materialise the metadata mapping into a fresh dict[str, str].
        metadata_copy: dict[str, str] = {
            str(k): str(v) for k, v in execution.metadata.items()
        }

        return cls(
            id=execution.id,
            job_name=execution.job_name,
            started_at=started_at_naive,
            finished_at=finished_at_naive,
            status=execution.status.value,
            error_message=execution.error_message,
            metadata_json=metadata_copy,
        )


class BackfillTaskModel(SQLModel, table=True):
    """Database model for :class:`BackfillTask` (Phase J — Task #212 Layer 2).

    Queued historical-data fetch for one ticker over one date range.
    The :class:`HistoricalDataPrewarmer` writes rows in ``PENDING`` state
    after a strategy activation; the scheduler's pickup loop drains them
    and the in-memory state machine flips ``PENDING -> RUNNING ->
    SUCCEEDED`` / ``FAILED``.

    Indexes:

    * ``(status, created_at)`` — backs the scheduler's pending-pickup
      query (``WHERE status = 'pending' ORDER BY created_at ASC``).

    Attributes:
        id: Primary key (UUID).
        ticker: Stock symbol (≤ 10 chars — generous against the Ticker
            VO's 1–5 constraint to absorb future format changes).
        start_date: First trading day of the range (inclusive).
        end_date: Last trading day of the range (inclusive).
        priority: ``low`` (activation-driven) or ``high`` (operator).
        status: Lifecycle stage as a string (mirrors
            :class:`BackfillTaskStatus`).
        created_at: Naive UTC timestamp when the row was inserted.
        finished_at: Naive UTC timestamp when the task reached a
            terminal status. ``None`` while PENDING / RUNNING.
        error_message: Truncated reason for FAILED rows (≤ 500 chars).
    """

    __tablename__ = "backfill_tasks"  # type: ignore[assignment]
    __table_args__ = (
        Index(
            "idx_backfill_tasks_status_created_at",
            "status",
            "created_at",
        ),
    )

    id: UUID = Field(primary_key=True)
    ticker: str = Field(max_length=10, index=True)
    start_date: date
    end_date: date
    priority: str = Field(max_length=10)
    status: str = Field(max_length=20)
    created_at: datetime
    finished_at: datetime | None = Field(default=None)
    error_message: str | None = Field(default=None, max_length=500)

    def to_domain(self) -> BackfillTask:
        """Convert database model to domain entity.

        Raises:
            ValueError: If ``status`` or ``priority`` drift from their
                respective enums, or if the ticker symbol is invalid.
        """
        created_at_utc = self.created_at.replace(tzinfo=UTC)
        finished_at_utc = (
            self.finished_at.replace(tzinfo=UTC)
            if self.finished_at is not None
            else None
        )
        status = BackfillTaskStatus(self.status)
        priority = BackfillPriority(self.priority)
        ticker = Ticker(self.ticker)

        return BackfillTask(
            id=self.id,
            ticker=ticker,
            start_date=self.start_date,
            end_date=self.end_date,
            priority=priority,
            status=status,
            created_at=created_at_utc,
            finished_at=finished_at_utc,
            error_message=self.error_message,
        )

    @classmethod
    def from_domain(cls, task: BackfillTask) -> "BackfillTaskModel":
        """Convert domain entity to database model."""
        created_at_naive = _strip_tz(task.created_at) or task.created_at
        finished_at_naive = _strip_tz(task.finished_at)

        return cls(
            id=task.id,
            ticker=task.ticker.symbol,
            start_date=task.start_date,
            end_date=task.end_date,
            priority=task.priority.value,
            status=task.status.value,
            created_at=created_at_naive,
            finished_at=finished_at_naive,
            error_message=task.error_message,
        )
