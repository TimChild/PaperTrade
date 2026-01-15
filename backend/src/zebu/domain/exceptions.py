"""Domain layer exceptions.

All domain exceptions inherit from DomainException to allow catching all domain errors.
These exceptions represent business rule violations and invalid domain states.
"""


class DomainException(Exception):
    """Base exception for all domain layer errors."""

    pass


# Value Object Exceptions


class InvalidValueObjectError(DomainException):
    """Base exception for invalid value object construction."""

    pass


class InvalidMoneyError(InvalidValueObjectError):
    """Raised when Money value object construction or operation fails."""

    pass


class InvalidTickerError(InvalidValueObjectError):
    """Raised when Ticker value object validation fails."""

    pass


class InvalidQuantityError(InvalidValueObjectError):
    """Raised when Quantity value object validation fails."""

    pass


# Entity Exceptions


class InvalidEntityError(DomainException):
    """Base exception for invalid entity construction."""

    pass


class InvalidPortfolioError(InvalidEntityError):
    """Raised when Portfolio entity invariants are violated."""

    pass


class PortfolioNotFoundError(InvalidEntityError):
    """Raised when a portfolio cannot be found by ID."""

    def __init__(self, portfolio_id: str) -> None:
        """Initialize PortfolioNotFoundError.

        Args:
            portfolio_id: ID of the portfolio that was not found
        """
        self.portfolio_id = portfolio_id
        super().__init__(f"Portfolio not found: {portfolio_id}")


class InvalidTransactionError(InvalidEntityError):
    """Raised when Transaction entity invariants are violated."""

    pass


# Business Rule Violation Exceptions


class BusinessRuleViolationError(DomainException):
    """Base exception for business rule violations."""

    pass


class InsufficientFundsError(BusinessRuleViolationError):
    """Raised when attempting to withdraw more cash than available.

    Attributes:
        available: Amount of cash currently available
        required: Amount of cash needed for the operation
        message: Human-readable error message
    """

    def __init__(
        self,
        available: "Money",  # type: ignore  # Forward reference to avoid circular import  # noqa: F821
        required: "Money",  # type: ignore  # noqa: F821
        message: str | None = None,
    ) -> None:
        """Initialize InsufficientFundsError with amount details.

        Args:
            available: Amount currently available
            required: Amount needed
            message: Optional custom message (auto-generated if not provided)
        """
        from zebu.domain.value_objects.money import Money

        if not isinstance(available, Money):
            raise TypeError(f"available must be Money, got {type(available)}")
        if not isinstance(required, Money):
            raise TypeError(f"required must be Money, got {type(required)}")
        if available.currency != required.currency:
            raise ValueError("available and required must have same currency")

        self.available = available
        self.required = required

        if message is None:
            shortfall = required.subtract(available)
            message = (
                f"Insufficient funds. You have {available} but need {required} "
                f"for this trade (shortfall: {shortfall})"
            )

        self.message = message
        super().__init__(message)


class InsufficientSharesError(BusinessRuleViolationError):
    """Raised when attempting to sell more shares than owned.

    Attributes:
        ticker: Stock ticker symbol
        available: Number of shares currently owned
        required: Number of shares needed for the sale
        message: Human-readable error message
    """

    def __init__(
        self,
        ticker: str,
        available: "Quantity",  # type: ignore  # Forward reference  # noqa: F821
        required: "Quantity",  # type: ignore  # noqa: F821
        message: str | None = None,
    ) -> None:
        """Initialize InsufficientSharesError with share details.

        Args:
            ticker: Stock ticker symbol
            available: Shares currently owned
            required: Shares needed for sale
            message: Optional custom message (auto-generated if not provided)
        """
        from zebu.domain.value_objects.quantity import Quantity

        if not isinstance(available, Quantity):
            raise TypeError(f"available must be Quantity, got {type(available)}")
        if not isinstance(required, Quantity):
            raise TypeError(f"required must be Quantity, got {type(required)}")

        self.ticker = ticker
        self.available = available
        self.required = required

        if message is None:
            shortfall = required.shares - available.shares
            message = (
                f"Insufficient shares of {ticker}. You have {available.shares} shares "
                f"but need {required.shares} shares (shortfall: {shortfall})"
            )

        self.message = message
        super().__init__(message)


# Authentication Exceptions


class AuthenticationError(DomainException):
    """Base exception for authentication-related errors."""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid, expired, or malformed."""

    pass
