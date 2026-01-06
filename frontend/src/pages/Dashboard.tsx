import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { usePortfolios, usePortfolioBalance } from '@/hooks/usePortfolio'
import { useHoldings } from '@/hooks/useHoldings'
import { useTransactions } from '@/hooks/useTransactions'
import { PortfolioSummaryCard } from '@/components/features/portfolio/PortfolioSummaryCard'
import { HoldingsTable } from '@/components/features/portfolio/HoldingsTable'
import { TransactionList } from '@/components/features/portfolio/TransactionList'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'
import { EmptyState } from '@/components/ui/EmptyState'
import { Dialog } from '@/components/ui/Dialog'
import { CreatePortfolioForm } from '@/components/features/portfolio/CreatePortfolioForm'
import { adaptPortfolio, adaptHolding, adaptTransaction } from '@/utils/adapters'

export function Dashboard(): React.JSX.Element {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const navigate = useNavigate()
  const { data: portfolios, isLoading: portfoliosLoading, isError, error } = usePortfolios()

  // For the dashboard, we'll show the first portfolio
  const primaryPortfolioDTO = portfolios?.[0]
  const portfolioId = primaryPortfolioDTO?.id || ''

  const { data: balanceData, isLoading: balanceLoading } = usePortfolioBalance(portfolioId)
  const { data: holdingsData, isLoading: holdingsLoading } = useHoldings(portfolioId)
  const { data: transactionsData, isLoading: transactionsLoading } = useTransactions(portfolioId)

  // Adapt backend DTOs to frontend types
  const primaryPortfolio = primaryPortfolioDTO
    ? adaptPortfolio(primaryPortfolioDTO, balanceData || null)
    : null

  const holdings = holdingsData?.holdings.map(adaptHolding) || []
  const transactions = transactionsData?.transactions.map(adaptTransaction) || []

  if (isError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorDisplay error={error} />
      </div>
    )
  }

  // Show loading spinner while initial data loads
  if (portfoliosLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="py-12" />
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            Portfolio Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Track your investments and performance
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          data-testid="create-portfolio-header-btn"
          className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Create Portfolio
        </button>
      </header>

      <div className="space-y-8">
        {/* Portfolio Summary */}
        <section>
          {balanceLoading ? (
            <PortfolioSummaryCard
              portfolio={{
                id: '',
                name: 'Loading...',
                userId: '',
                cashBalance: 0,
                totalValue: 0,
                dailyChange: 0,
                dailyChangePercent: 0,
                createdAt: '',
              }}
              isLoading={true}
            />
          ) : primaryPortfolio ? (
            <div>
              <PortfolioSummaryCard portfolio={primaryPortfolio} />
              {portfolios && portfolios.length > 1 && (
                <div className="mt-4">
                  <p className="text-sm text-gray-600 dark:text-gray-400">
                    You have {portfolios.length} portfolios.{' '}
                    <Link
                      to={`/portfolio/${primaryPortfolio.id}`}
                      className="text-blue-600 hover:underline dark:text-blue-400"
                    >
                      View details
                    </Link>
                  </p>
                </div>
              )}
            </div>
          ) : (
            <EmptyState
              message="No portfolios found. Create your first portfolio to get started!"
              action={
                <button
                  onClick={() => setShowCreateModal(true)}
                  data-testid="create-first-portfolio-btn"
                  className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Create Your First Portfolio
                </button>
              }
            />
          )}
        </section>

        {/* Holdings */}
        {primaryPortfolio && (
          <section>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
                Holdings
              </h2>
              <Link
                to={`/portfolio/${primaryPortfolio.id}`}
                className="text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                View all
              </Link>
            </div>
            <HoldingsTable holdings={holdings} isLoading={holdingsLoading} />
          </section>
        )}

        {/* Recent Transactions */}
        {primaryPortfolio && (
          <section>
            <div className="mb-4 flex items-center justify-between">
              <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
                Recent Transactions
              </h2>
              <Link
                to={`/portfolio/${primaryPortfolio.id}`}
                className="text-sm text-blue-600 hover:underline dark:text-blue-400"
              >
                View all
              </Link>
            </div>
            <TransactionList
              transactions={transactions}
              limit={5}
              isLoading={transactionsLoading}
            />
          </section>
        )}

        {/* Quick Actions */}
        {primaryPortfolio && (
          <section>
            <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
              Quick Actions
            </h2>
            <div className="flex gap-4">
              <Link
                to={`/portfolio/${primaryPortfolio.id}`}
                data-testid="dashboard-trade-stocks-link"
                className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700"
              >
                Trade Stocks
              </Link>
              <button
                className="rounded-lg border border-gray-300 bg-white px-6 py-3 font-semibold text-gray-700 transition-colors hover:bg-gray-50 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                onClick={() => alert('Deposit feature coming soon!')}
              >
                Deposit Funds
              </button>
            </div>
          </section>
        )}
      </div>

      {/* Portfolio Creation Modal */}
      <Dialog
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="Create New Portfolio"
        className="max-w-md"
      >
        <CreatePortfolioForm
          onSuccess={(portfolioId) => {
            setShowCreateModal(false)
            // Navigate to the newly created portfolio so user can see it immediately
            navigate(`/portfolio/${portfolioId}`)
          }}
          onCancel={() => setShowCreateModal(false)}
        />
      </Dialog>
    </div>
  )
}
