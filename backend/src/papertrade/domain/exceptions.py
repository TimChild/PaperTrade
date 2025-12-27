"""Domain-specific exceptions."""


class DomainError(Exception):
    """Base class for domain errors."""

    pass


class InsufficientFundsError(DomainError):
    """Raised when a trade exceeds available cash."""

    pass


class InsufficientSharesError(DomainError):
    """Raised when selling more shares than owned."""

    pass


class InvalidTransactionError(DomainError):
    """Raised when a transaction violates business rules."""

    pass
