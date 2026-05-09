"""Strategy entity - Represents an algorithmic trading strategy definition."""

from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from zebu.domain.exceptions import InvalidStrategyError
from zebu.domain.value_objects.strategy_parameters import (
    StrategyParameters,
    parameters_for_type,
)
from zebu.domain.value_objects.strategy_type import StrategyType


@dataclass(frozen=True)
class Strategy:
    """Represents a user-defined algorithmic trading strategy.

    A strategy defines *how* a backtest is executed: which tickers to trade,
    what algorithm to apply, and any algorithm-specific parameters.

    Strategy is fully immutable after creation. Equality and hashing are based
    on ``id`` only so that strategies can be used in sets and as dict keys.

    The ``parameters`` field is a discriminated union of typed parameter
    dataclasses (see :mod:`zebu.domain.value_objects.strategy_parameters`).
    The concrete subtype must match ``strategy_type`` — this is enforced at
    construction.

    Attributes:
        id: Unique strategy identifier
        user_id: Owner of the strategy
        name: Human-readable name (1-100 characters)
        strategy_type: Algorithm used by this strategy
        tickers: List of ticker symbols (1-10 items)
        parameters: Typed algorithm-specific configuration matching
            ``strategy_type`` (BuyAndHoldParameters, DcaParameters, or
            MaCrossoverParameters).
        created_at: When the strategy was created (UTC)

    Raises:
        InvalidStrategyError: If any invariant is violated, including the
            type of ``parameters`` not matching ``strategy_type``.
    """

    id: UUID
    user_id: UUID
    name: str
    strategy_type: StrategyType
    tickers: list[str]
    parameters: StrategyParameters
    created_at: datetime

    def __post_init__(self) -> None:
        """Validate Strategy invariants after initialization."""
        if not self.name or not self.name.strip():
            raise InvalidStrategyError("Strategy name cannot be empty or whitespace")
        if len(self.name) > 100:
            raise InvalidStrategyError(
                f"Strategy name must be maximum 100 characters, got {len(self.name)}"
            )
        if not (1 <= len(self.tickers) <= 10):
            raise InvalidStrategyError("Strategy must have between 1 and 10 tickers")

        # Discriminator check: enforce that the typed parameters concrete type
        # matches strategy_type. This is the only post-typing invariant — the
        # type system already ensures ``parameters`` is one of the union
        # members, so a separate "is dataclass instance" check would be
        # redundant under strict Pyright.
        if not parameters_for_type(self.strategy_type, self.parameters):
            raise InvalidStrategyError(
                f"parameters type {type(self.parameters).__name__} does not match "
                f"strategy_type {self.strategy_type.value}"
            )

        now = datetime.now(UTC)
        created_at_utc = (
            self.created_at
            if self.created_at.tzinfo is not None
            else self.created_at.replace(tzinfo=UTC)
        )
        if created_at_utc > now:
            raise InvalidStrategyError("Strategy created_at cannot be in the future")

    def __eq__(self, other: object) -> bool:
        """Equality based on ID only.

        Args:
            other: Object to compare

        Returns:
            True if other is Strategy with same ID
        """
        if not isinstance(other, Strategy):
            return False
        return self.id == other.id

    def __hash__(self) -> int:
        """Hash based on ID for use in dicts/sets.

        Returns:
            Hash of strategy ID
        """
        return hash(self.id)

    def __repr__(self) -> str:
        """Return repr for debugging.

        Returns:
            String like "Strategy(id=UUID('...'), name='My Strategy')"
        """
        return f"Strategy(id={self.id}, user_id={self.user_id}, name='{self.name}')"
