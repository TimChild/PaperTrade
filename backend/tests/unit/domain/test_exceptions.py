"""Tests for domain exceptions hierarchy."""

import pytest

from papertrade.domain.exceptions import (
    BusinessRuleViolationError,
    DomainException,
    InsufficientFundsError,
    InsufficientSharesError,
    InvalidEntityError,
    InvalidMoneyError,
    InvalidPortfolioError,
    InvalidQuantityError,
    InvalidTickerError,
    InvalidTransactionError,
    InvalidValueObjectError,
)


class TestExceptionHierarchy:
    """Tests that exception hierarchy is correctly defined."""

    def test_domain_exception_is_base(self) -> None:
        """All domain exceptions should inherit from DomainException."""
        # Value object exceptions
        assert issubclass(InvalidValueObjectError, DomainException)
        assert issubclass(InvalidMoneyError, DomainException)
        assert issubclass(InvalidTickerError, DomainException)
        assert issubclass(InvalidQuantityError, DomainException)

        # Entity exceptions
        assert issubclass(InvalidEntityError, DomainException)
        assert issubclass(InvalidPortfolioError, DomainException)
        assert issubclass(InvalidTransactionError, DomainException)

        # Business rule exceptions
        assert issubclass(BusinessRuleViolationError, DomainException)
        assert issubclass(InsufficientFundsError, DomainException)
        assert issubclass(InsufficientSharesError, DomainException)

    def test_value_object_exceptions_hierarchy(self) -> None:
        """Value object exceptions should inherit from InvalidValueObjectError."""
        assert issubclass(InvalidMoneyError, InvalidValueObjectError)
        assert issubclass(InvalidTickerError, InvalidValueObjectError)
        assert issubclass(InvalidQuantityError, InvalidValueObjectError)

    def test_entity_exceptions_hierarchy(self) -> None:
        """Entity exceptions should inherit from InvalidEntityError."""
        assert issubclass(InvalidPortfolioError, InvalidEntityError)
        assert issubclass(InvalidTransactionError, InvalidEntityError)

    def test_business_rule_exceptions_hierarchy(self) -> None:
        """Business rule exceptions should inherit from BusinessRuleViolationError."""
        assert issubclass(InsufficientFundsError, BusinessRuleViolationError)
        assert issubclass(InsufficientSharesError, BusinessRuleViolationError)

    def test_exceptions_can_be_raised_and_caught(self) -> None:
        """All exceptions should be raisable and catchable."""
        with pytest.raises(DomainException):
            raise InvalidMoneyError("Test error")

        with pytest.raises(InvalidValueObjectError):
            raise InvalidTickerError("Test error")

        # InsufficientFundsError now requires Money objects, not just a message
        # Test in test_enhanced_exceptions.py instead

    def test_exception_messages_are_descriptive(self) -> None:
        """Exceptions should carry descriptive messages."""
        msg = "Amount cannot be negative"
        exc = InvalidMoneyError(msg)
        assert str(exc) == msg

        # InsufficientFundsError now requires Money objects, not just a message
        # Test in test_enhanced_exceptions.py instead
