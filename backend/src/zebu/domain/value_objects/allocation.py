"""Allocation value object - weighted distribution of money across tickers."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from decimal import Decimal

from zebu.domain.exceptions import InvalidAllocationError
from zebu.domain.value_objects.ticker import Ticker

# Tolerance for "weights sum to 1.0" check. Decimal-based to avoid float
# round-off in serialised inputs (e.g. {"AAPL": 0.6, "GOOGL": 0.4}).
_SUM_TOLERANCE = Decimal("0.001")
_TARGET_SUM = Decimal("1")


@dataclass(frozen=True)
class Allocation:
    """Represents a weighted distribution of money across tickers.

    Allocation is an immutable value object. Weights must each be in ``[0, 1]``
    and sum to ``1.0`` (within :data:`_SUM_TOLERANCE`). Tickers are stored as
    :class:`Ticker` value objects.

    Attributes:
        weights: Mapping from Ticker to its allocation fraction (Decimal in [0, 1])

    Raises:
        InvalidAllocationError: If weights are empty, contain negative values,
            or do not sum to 1.0 within tolerance.
    """

    weights: Mapping[Ticker, Decimal] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate Allocation invariants after initialization."""
        if not self.weights:
            raise InvalidAllocationError("Allocation must contain at least one ticker")

        for ticker, fraction in self.weights.items():
            if not fraction.is_finite():
                raise InvalidAllocationError(
                    f"Allocation weight for {ticker} must be finite"
                )
            if fraction < Decimal("0") or fraction > Decimal("1"):
                raise InvalidAllocationError(
                    f"Allocation weight for {ticker} must be in [0, 1], got {fraction}"
                )

        total = sum(self.weights.values(), Decimal("0"))
        if abs(total - _TARGET_SUM) > _SUM_TOLERANCE:
            raise InvalidAllocationError(
                f"Allocation weights must sum to 1.0 (within tolerance "
                f"{_SUM_TOLERANCE}), got {total}"
            )

    @classmethod
    def from_raw(cls, raw: Mapping[str, float | Decimal | int | str]) -> "Allocation":
        """Build an Allocation from a raw mapping of symbol strings to numeric weights.

        Used at the adapter boundary where weights arrive as JSON floats or as
        Decimal values from persisted strategy parameters.

        Args:
            raw: Mapping of ticker symbol (str) to fraction (float, Decimal,
                int, or str)

        Returns:
            Validated Allocation

        Raises:
            InvalidAllocationError: If the resulting weights are invalid
        """
        if not raw:
            raise InvalidAllocationError("Allocation must contain at least one ticker")

        normalised: dict[Ticker, Decimal] = {}
        for symbol, fraction in raw.items():
            ticker = Ticker(symbol)
            try:
                value = (
                    fraction
                    if isinstance(fraction, Decimal)
                    else Decimal(str(fraction))
                )
            except Exception as exc:
                raise InvalidAllocationError(
                    f"Invalid allocation value for {ticker}: {fraction!r}"
                ) from exc
            normalised[ticker] = value
        return cls(weights=normalised)

    def fraction_for(self, ticker: Ticker) -> Decimal:
        """Return the fraction for ``ticker`` (zero if not present).

        Args:
            ticker: Ticker to query

        Returns:
            Allocation fraction as Decimal (0 if ticker not in allocation)
        """
        return self.weights.get(ticker, Decimal("0"))

    def tickers(self) -> tuple[Ticker, ...]:
        """Return the tuple of tickers in this allocation."""
        return tuple(self.weights.keys())

    def __hash__(self) -> int:
        """Hash based on a tuple of (ticker, fraction) sorted by symbol."""
        items = tuple(
            (t.symbol, str(f))
            for t, f in sorted(self.weights.items(), key=lambda kv: kv[0].symbol)
        )
        return hash(items)

    def __eq__(self, other: object) -> bool:
        """Equality based on weights mapping."""
        if not isinstance(other, Allocation):
            return False
        if set(self.weights.keys()) != set(other.weights.keys()):
            return False
        return all(self.weights[t] == other.weights[t] for t in self.weights)
