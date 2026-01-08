"""DeletePortfolio command - Delete a portfolio and all related data."""

from dataclasses import dataclass
from uuid import UUID

from papertrade.application.ports.portfolio_repository import PortfolioRepository
from papertrade.application.ports.snapshot_repository import SnapshotRepository
from papertrade.application.ports.transaction_repository import TransactionRepository
from papertrade.domain.exceptions import PortfolioNotFoundError


@dataclass(frozen=True)
class DeletePortfolioCommand:
    """Input data for deleting a portfolio.

    Attributes:
        portfolio_id: ID of the portfolio to delete
        user_id: ID of the user requesting deletion (for ownership verification)
    """

    portfolio_id: UUID
    user_id: UUID


class DeletePortfolioHandler:
    """Handler for DeletePortfolio command.

    Deletes a portfolio and all related data (transactions, snapshots) in the
    correct order to maintain referential integrity.
    """

    def __init__(
        self,
        portfolio_repository: PortfolioRepository,
        transaction_repository: TransactionRepository,
        snapshot_repository: SnapshotRepository,
    ) -> None:
        """Initialize handler with repository dependencies.

        Args:
            portfolio_repository: Repository for portfolio persistence
            transaction_repository: Repository for transaction persistence
            snapshot_repository: Repository for snapshot persistence
        """
        self._portfolio_repository = portfolio_repository
        self._transaction_repository = transaction_repository
        self._snapshot_repository = snapshot_repository

    async def execute(self, command: DeletePortfolioCommand) -> None:
        """Execute the DeletePortfolio command.

        Deletes a portfolio and all related data. Verifies portfolio exists and
        belongs to the requesting user before deletion.

        Args:
            command: Command with portfolio deletion parameters

        Raises:
            PortfolioNotFoundError: If portfolio doesn't exist
            PermissionError: If user doesn't own the portfolio
        """
        # Verify portfolio exists
        portfolio = await self._portfolio_repository.get(command.portfolio_id)
        if portfolio is None:
            raise PortfolioNotFoundError(str(command.portfolio_id))

        # Verify user owns this portfolio
        if portfolio.user_id != command.user_id:
            raise PermissionError(
                f"User {command.user_id} does not own portfolio {command.portfolio_id}"
            )

        # Delete related data in correct order to maintain referential integrity
        # 1. Delete snapshots (they reference portfolio)
        await self._snapshot_repository.delete_by_portfolio(command.portfolio_id)

        # 2. Delete transactions (they reference portfolio)
        await self._transaction_repository.delete_by_portfolio(command.portfolio_id)

        # 3. Finally delete the portfolio itself
        await self._portfolio_repository.delete(command.portfolio_id)
