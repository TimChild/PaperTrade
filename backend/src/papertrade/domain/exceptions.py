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


# Authentication & Authorization Exceptions


class UserNotFoundError(DomainException):
    """Raised when a user cannot be found."""

    pass


class InvalidCredentialsError(DomainException):
    """Raised when authentication credentials are invalid."""

    pass


class DuplicateEmailError(DomainException):
    """Raised when attempting to register with an email that already exists."""

    pass


class InvalidTokenError(DomainException):
    """Raised when a JWT token is invalid or expired."""

    pass


class InactiveUserError(DomainException):
    """Raised when a user account is inactive."""

    pass
