import { useParams, Link } from 'react-router-dom'
import { usePortfolio } from '@/hooks/usePortfolio'
import { useHoldings } from '@/hooks/useHoldings'
import { useTransactions, useExecuteTrade } from '@/hooks/useTransactions'
import { PortfolioSummaryCard } from '@/components/features/portfolio/PortfolioSummaryCard'
import { HoldingsTable } from '@/components/features/portfolio/HoldingsTable'
import { TransactionList } from '@/components/features/portfolio/TransactionList'
import { TradeForm } from '@/components/features/portfolio/TradeForm'
import type { TradeRequest } from '@/types/portfolio'

export function PortfolioDetail(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const portfolioId = id || ''

  const { data: portfolio, isLoading: portfolioLoading, isError, error } = usePortfolio(portfolioId)
  const { data: holdings, isLoading: holdingsLoading } = useHoldings(portfolioId)
  const { data: transactions, isLoading: transactionsLoading } = useTransactions(portfolioId)
  const executeTrade = useExecuteTrade()

  const handleTradeSubmit = (trade: TradeRequest) => {
    executeTrade.mutate(trade, {
      onSuccess: () => {
        alert(`${trade.action === 'buy' ? 'Buy' : 'Sell'} order executed successfully!`)
      },
      onError: (error) => {
        alert(`Failed to execute trade: ${error instanceof Error ? error.message : 'Unknown error'}`)
      },
    })
  }

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
          <Link
            to="/dashboard"
            className="mt-4 inline-block text-blue-600 hover:underline dark:text-blue-400"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header with navigation */}
      <div className="mb-6">
        <Link
          to="/dashboard"
          className="mb-4 inline-flex items-center text-blue-600 hover:underline dark:text-blue-400"
        >
          ← Back to Dashboard
        </Link>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
          {portfolio?.name || 'Portfolio Details'}
        </h1>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="space-y-8 lg:col-span-2">
          {/* Portfolio Summary */}
          <section>
            {portfolioLoading || !portfolio ? (
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
            ) : (
              <PortfolioSummaryCard portfolio={portfolio} />
            )}
          </section>

          {/* Performance Chart Placeholder */}
          <section>
            <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
              Performance
            </h2>
            <div className="flex h-64 items-center justify-center rounded-lg border border-gray-300 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
              <p className="text-gray-600 dark:text-gray-400">
                Performance chart coming soon
              </p>
            </div>
          </section>

          {/* Holdings */}
          <section>
            <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
              Holdings
            </h2>
            <HoldingsTable
              holdings={holdings || []}
              isLoading={holdingsLoading}
            />
          </section>

          {/* Transaction History */}
          <section>
            <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
              Transaction History
            </h2>
            <TransactionList
              transactions={transactions || []}
              isLoading={transactionsLoading}
            />
          </section>
        </div>

        {/* Sidebar */}
        <div className="space-y-8 lg:col-span-1">
          {/* Trade Form */}
          <section>
            <TradeForm
              portfolioId={portfolioId}
              onSubmit={handleTradeSubmit}
              isSubmitting={executeTrade.isPending}
            />
          </section>
        </div>
      </div>
    </div>
  )
}
