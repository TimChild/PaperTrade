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


class InvalidTransactionError(InvalidEntityError):
    """Raised when Transaction entity invariants are violated."""

    pass


# Business Rule Violation Exceptions


class BusinessRuleViolationError(DomainException):
    """Base exception for business rule violations."""

    pass


class InsufficientFundsError(BusinessRuleViolationError):
    """Raised when attempting to withdraw more cash than available."""

    pass


class InsufficientSharesError(BusinessRuleViolationError):
    """Raised when attempting to sell more shares than owned."""

    pass


# Authentication Exceptions


class AuthenticationError(DomainException):
    """Base exception for authentication-related errors."""

    pass


class InvalidTokenError(AuthenticationError):
    """Raised when a token is invalid, expired, or malformed."""

    pass
