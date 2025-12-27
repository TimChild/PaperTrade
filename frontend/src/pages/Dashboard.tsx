import { Link } from 'react-router-dom'
import { usePortfolios } from '@/hooks/usePortfolio'
import { useHoldings } from '@/hooks/useHoldings'
import { useTransactions } from '@/hooks/useTransactions'
import { PortfolioSummaryCard } from '@/components/features/portfolio/PortfolioSummaryCard'
import { HoldingsTable } from '@/components/features/portfolio/HoldingsTable'
import { TransactionList } from '@/components/features/portfolio/TransactionList'

export function Dashboard(): React.JSX.Element {
  const { data: portfolios, isLoading: portfoliosLoading, isError, error } = usePortfolios()

  // For the dashboard, we'll show the first portfolio
  const primaryPortfolio = portfolios?.[0]
  const portfolioId = primaryPortfolio?.id || ''

  const { data: holdings, isLoading: holdingsLoading } = useHoldings(portfolioId)
  const { data: transactions, isLoading: transactionsLoading } = useTransactions(portfolioId)

  if (isError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <div className="rounded-lg border border-red-300 bg-red-50 p-6 dark:border-red-700 dark:bg-red-900/20">
          <h2 className="text-xl font-semibold text-red-700 dark:text-red-400">
            Error Loading Portfolio
          </h2>
          <p className="mt-2 text-red-600 dark:text-red-500">
            {error instanceof Error ? error.message : 'Failed to load portfolio data'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-8">
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
          Portfolio Dashboard
        </h1>
        <p className="mt-2 text-gray-600 dark:text-gray-400">
          Track your investments and performance
        </p>
      </header>

      <div className="space-y-8">
        {/* Portfolio Summary */}
        <section>
          {portfoliosLoading ? (
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
            <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-gray-600 dark:text-gray-400">
                No portfolios found. Create your first portfolio to get started.
              </p>
            </div>
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
            <HoldingsTable
              holdings={holdings || []}
              isLoading={holdingsLoading}
            />
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
              transactions={transactions || []}
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
    </div>
  )
}
