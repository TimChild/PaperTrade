"""Portfolio snapshot entity - Daily snapshot of portfolio value for analytics."""

from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from zebu.domain.exceptions import InvalidPortfolioError


@dataclass(frozen=True)
class HoldingBreakdown:
    """Value of a single holding at snapshot time.

    Attributes:
        ticker: Stock ticker symbol
        quantity: Number of shares held
        price_per_share: Price per share at snapshot time
        value: Total value (quantity * price_per_share)
    """

    ticker: str
    quantity: int
    price_per_share: Decimal
    value: Decimal


@dataclass(frozen=True)
class PortfolioSnapshot:
    """Daily snapshot of portfolio value for analytics.

    A snapshot represents the state of a portfolio at the end of a specific day.
    Snapshots are used for historical analytics, performance charts, and backtesting.

    Attributes:
        id: Unique snapshot identifier
        portfolio_id: Portfolio this snapshot belongs to
        snapshot_date: Date of this snapshot (end-of-day)
        total_value: Total portfolio value (cash + holdings)
        cash_balance: Available cash in portfolio
        holdings_value: Total value of all stock holdings
        holdings_count: Number of unique stocks held
        created_at: When this snapshot was calculated
        holdings_breakdown: Per-holding value breakdown at snapshot time

    Invariants:
        - total_value == cash_balance + holdings_value (always)
        - snapshot_date <= today (cannot snapshot future)
        - All monetary values are non-negative
        - holdings_count >= 0
        - sum(h.value for h in holdings_breakdown) == holdings_value when non-empty
    """

    id: UUID
    portfolio_id: UUID
    snapshot_date: date
    total_value: Decimal
    cash_balance: Decimal
    holdings_value: Decimal
    holdings_count: int
    created_at: datetime
    holdings_breakdown: list[HoldingBreakdown] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate PortfolioSnapshot invariants after initialization."""
        # Validate total_value = cash_balance + holdings_value
        expected_total = self.cash_balance + self.holdings_value
        if self.total_value != expected_total:
            raise InvalidPortfolioError(
                f"total_value must equal cash_balance + holdings_value. "
                f"Expected {expected_total}, got {self.total_value}"
            )

        # Validate snapshot_date is not in future
        today = date.today()
        if self.snapshot_date > today:
            raise InvalidPortfolioError(
                f"snapshot_date cannot be in the future. "
                f"Got {self.snapshot_date}, today is {today}"
            )

        # Validate non-negative monetary values
        if self.cash_balance < 0:
            raise InvalidPortfolioError(
                f"cash_balance cannot be negative. Got {self.cash_balance}"
            )
        if self.holdings_value < 0:
            raise InvalidPortfolioError(
                f"holdings_value cannot be negative. Got {self.holdings_value}"
            )
        if self.total_value < 0:
            raise InvalidPortfolioError(
                f"total_value cannot be negative. Got {self.total_value}"
            )

        # Validate holdings_count is non-negative
        if self.holdings_count < 0:
            raise InvalidPortfolioError(
                f"holdings_count cannot be negative. Got {self.holdings_count}"
            )

        # Validate holdings_breakdown sum matches holdings_value when non-empty
        if self.holdings_breakdown:
            breakdown_total = sum(h.value for h in self.holdings_breakdown)
            if breakdown_total != self.holdings_value:
                raise InvalidPortfolioError(
                    f"sum of holdings_breakdown values must equal holdings_value. "
                    f"Expected {self.holdings_value}, got {breakdown_total}"
                )

    @classmethod
    def create(
        cls,
        portfolio_id: UUID,
        snapshot_date: date,
        cash_balance: Decimal,
        holdings_value: Decimal,
        holdings_count: int,
        holdings_breakdown: list[HoldingBreakdown] | None = None,
    ) -> "PortfolioSnapshot":
        """Factory method to create a new snapshot.

        Args:
            portfolio_id: Portfolio this snapshot belongs to
            snapshot_date: Date of this snapshot
            cash_balance: Available cash
            holdings_value: Total value of holdings
            holdings_count: Number of unique stocks
            holdings_breakdown: Per-holding value breakdown (optional)

        Returns:
            New PortfolioSnapshot with auto-generated ID and timestamp
        """
        return cls(
            id=uuid4(),
            portfolio_id=portfolio_id,
            snapshot_date=snapshot_date,
            total_value=cash_balance + holdings_value,
            cash_balance=cash_balance,
            holdings_value=holdings_value,
            holdings_count=holdings_count,
            created_at=datetime.now(UTC),
            holdings_breakdown=holdings_breakdown or [],
        )

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare

        Returns:
            True if other is PortfolioSnapshot with same ID
        """
        if not isinstance(other, PortfolioSnapshot):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of snapshot ID
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String representation of snapshot
        """
        return (
            f"PortfolioSnapshot(id={self.id}, "
            f"portfolio_id={self.portfolio_id}, "
            f"snapshot_date={self.snapshot_date}, "
            f"total_value={self.total_value})"
        )
