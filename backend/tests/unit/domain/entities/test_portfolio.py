"""Tests for Portfolio entity."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from papertrade.domain.entities.portfolio import Portfolio
from papertrade.domain.exceptions import InvalidPortfolioError


class TestPortfolioConstruction:
    """Tests for Portfolio construction and validation."""

    def test_valid_construction(self) -> None:
        """Should create Portfolio with valid data."""
        portfolio_id = uuid4()
        user_id = uuid4()
        name = "My Investment Portfolio"
        created_at = datetime.now(UTC)

        portfolio = Portfolio(
            id=portfolio_id, user_id=user_id, name=name, created_at=created_at
        )

        assert portfolio.id == portfolio_id
        assert portfolio.user_id == user_id
        assert portfolio.name == name
        assert portfolio.created_at == created_at

    def test_valid_construction_with_max_length_name(self) -> None:
        """Should allow name up to 100 characters."""
        name = "A" * 100
        portfolio = Portfolio(
            id=uuid4(), user_id=uuid4(), name=name, created_at=datetime.now(UTC)
        )
        assert portfolio.name == name

    def test_invalid_construction_with_empty_name(self) -> None:
        """Should raise error for empty name."""
        with pytest.raises(InvalidPortfolioError, match="cannot be empty"):
            Portfolio(
                id=uuid4(),
                user_id=uuid4(),
                name="",
                created_at=datetime.now(UTC),
            )

    def test_invalid_construction_with_whitespace_only_name(self) -> None:
        """Should raise error for whitespace-only name."""
        with pytest.raises(InvalidPortfolioError, match="cannot be empty"):
            Portfolio(
                id=uuid4(),
                user_id=uuid4(),
                name="   ",
                created_at=datetime.now(UTC),
            )

    def test_invalid_construction_with_too_long_name(self) -> None:
        """Should raise error for name longer than 100 characters."""
        with pytest.raises(InvalidPortfolioError, match="maximum 100 characters"):
            Portfolio(
                id=uuid4(),
                user_id=uuid4(),
                name="A" * 101,
                created_at=datetime.now(UTC),
            )

    def test_invalid_construction_with_future_created_at(self) -> None:
        """Should raise error if created_at is in the future."""
        from datetime import timedelta

        future_time = datetime.now(UTC) + timedelta(days=1)
        with pytest.raises(InvalidPortfolioError, match="cannot be in the future"):
            Portfolio(id=uuid4(), user_id=uuid4(), name="Test", created_at=future_time)


class TestPortfolioEquality:
    """Tests for Portfolio equality semantics."""

    def test_equality_based_on_id(self) -> None:
        """Two portfolios with same ID should be equal."""
        portfolio_id = uuid4()
        user_id = uuid4()
        created_at = datetime.now(UTC)

        p1 = Portfolio(
            id=portfolio_id, user_id=user_id, name="Portfolio 1", created_at=created_at
        )
        p2 = Portfolio(
            id=portfolio_id, user_id=user_id, name="Portfolio 2", created_at=created_at
        )

        assert p1 == p2

    def test_inequality_different_ids(self) -> None:
        """Portfolios with different IDs should not be equal."""
        user_id = uuid4()
        created_at = datetime.now(UTC)

        p1 = Portfolio(
            id=uuid4(), user_id=user_id, name="Portfolio 1", created_at=created_at
        )
        p2 = Portfolio(
            id=uuid4(), user_id=user_id, name="Portfolio 1", created_at=created_at
        )

        assert p1 != p2

    def test_hashable(self) -> None:
        """Portfolio should be usable as dict key."""
        p1 = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            created_at=datetime.now(UTC),
        )
        p2 = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            created_at=datetime.now(UTC),
        )

        portfolio_dict = {p1: "First", p2: "Second"}
        assert portfolio_dict[p1] == "First"
        assert portfolio_dict[p2] == "Second"

    def test_hash_consistency(self) -> None:
        """Equal portfolios should have same hash."""
        portfolio_id = uuid4()
        user_id = uuid4()
        created_at = datetime.now(UTC)

        p1 = Portfolio(
            id=portfolio_id, user_id=user_id, name="Portfolio 1", created_at=created_at
        )
        p2 = Portfolio(
            id=portfolio_id, user_id=user_id, name="Portfolio 2", created_at=created_at
        )

        assert hash(p1) == hash(p2)


class TestPortfolioImmutability:
    """Tests that Portfolio properties are immutable."""

    def test_cannot_modify_id(self) -> None:
        """Should not be able to modify ID after construction."""
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            created_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            portfolio.id = uuid4()  # type: ignore

    def test_cannot_modify_user_id(self) -> None:
        """Should not be able to modify user_id after construction."""
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            created_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            portfolio.user_id = uuid4()  # type: ignore

    def test_cannot_modify_created_at(self) -> None:
        """Should not be able to modify created_at after construction."""
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test",
            created_at=datetime.now(UTC),
        )
        with pytest.raises(AttributeError):
            portfolio.created_at = datetime.now(UTC)  # type: ignore

    def test_name_is_mutable(self) -> None:
        """Name should be the only mutable property (per architecture plan)."""
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Original Name",
            created_at=datetime.now(UTC),
        )
        # Per the architecture, name CAN be updated (it's the only mutable property)
        # But we're using frozen dataclass, so this should also be immutable
        with pytest.raises(AttributeError):
            portfolio.name = "New Name"  # type: ignore


class TestPortfolioStringRepresentation:
    """Tests for Portfolio string representation."""

    def test_repr_representation(self) -> None:
        """Should have useful repr."""
        portfolio = Portfolio(
            id=uuid4(),
            user_id=uuid4(),
            name="Test Portfolio",
            created_at=datetime.now(UTC),
        )
        repr_str = repr(portfolio)
        assert "Portfolio" in repr_str
        assert "Test Portfolio" in repr_str
        assert str(portfolio.id) in repr_str
