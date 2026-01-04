import { useParams, Link } from 'react-router-dom'
import { useRef, useState } from 'react'
import { usePortfolio, usePortfolioBalance, useExecuteTrade } from '@/hooks/usePortfolio'
import { useHoldings } from '@/hooks/useHoldings'
import { useTransactions } from '@/hooks/useTransactions'
import { PortfolioSummaryCard } from '@/components/features/portfolio/PortfolioSummaryCard'
import { HoldingsTable } from '@/components/features/portfolio/HoldingsTable'
import { TransactionList } from '@/components/features/portfolio/TransactionList'
import { TradeForm } from '@/components/features/portfolio/TradeForm'
import { PriceChart } from '@/components/features/PriceChart'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'
import { adaptPortfolio, adaptHolding, adaptTransaction } from '@/utils/adapters'
import type { TradeRequest } from '@/services/api/types'

export function PortfolioDetail(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const portfolioId = id || ''
  const tradeFormRef = useRef<HTMLElement>(null)
  const [quickSellData, setQuickSellData] = useState<{ ticker: string; quantity: number } | null>(null)

  const { data: portfolioDTO, isLoading: portfolioLoading, isError, error } = usePortfolio(portfolioId)
  const { data: balanceData, isLoading: balanceLoading } = usePortfolioBalance(portfolioId)
  const { data: holdingsData, isLoading: holdingsLoading } = useHoldings(portfolioId)
  const { data: transactionsData, isLoading: transactionsLoading } = useTransactions(portfolioId)
  const executeTrade = useExecuteTrade(portfolioId)

  // Adapt backend DTOs to frontend types
  const portfolio = portfolioDTO ? adaptPortfolio(portfolioDTO, balanceData || null) : null
  const holdings = holdingsData?.holdings.map(adaptHolding) || []
  const transactions = transactionsData?.transactions.map(adaptTransaction) || []

  const handleTradeSubmit = (trade: TradeRequest) => {
    console.log(`[TradeSubmit] Portfolio ID: ${portfolioId}, Action: ${trade.action}, Ticker: ${trade.ticker}, Quantity: ${trade.quantity}`)
    executeTrade.mutate(trade, {
      onSuccess: () => {
        alert(`${trade.action === 'BUY' ? 'Buy' : 'Sell'} order executed successfully!`)
        // Clear quick sell data after successful trade
        setQuickSellData(null)
      },
      onError: (error) => {
        console.error(`[TradeSubmit Error] Portfolio ID: ${portfolioId}`, error)
        alert(`Failed to execute trade: ${error instanceof Error ? error.message : 'Unknown error'}`)
      },
    })
  }

  const handleQuickSell = (ticker: string, quantity: number) => {
    // Set quick sell data and scroll to trade form
    setQuickSellData({ ticker, quantity })

    // Scroll to trade form with smooth behavior
    setTimeout(() => {
      tradeFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }, 100)
  }

  if (isError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorDisplay error={error} />
        <Link
          to="/dashboard"
          className="mt-4 inline-block text-blue-600 hover:underline dark:text-blue-400"
        >
          ← Back to Dashboard
        </Link>
      </div>
    )
  }

  if (portfolioLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="py-12" />
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      {/* Header with navigation */}
      <div className="mb-6">
        <Link
          to="/dashboard"
          data-testid="portfolio-detail-back-link"
          className="mb-4 inline-flex items-center text-blue-600 hover:underline dark:text-blue-400"
        >
          ← Back to Dashboard
        </Link>
        <h1 className="text-4xl font-bold text-gray-900 dark:text-white" data-testid="portfolio-detail-name">
          {portfolio?.name || 'Portfolio Details'}
        </h1>
      </div>

      <div className="grid gap-8 lg:grid-cols-3">
        {/* Main Content */}
        <div className="space-y-8 lg:col-span-2">
          {/* Portfolio Summary */}
          <section>
            {balanceLoading || !portfolio ? (
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
              <PortfolioSummaryCard
                portfolio={portfolio}
                holdingsDTO={holdingsData?.holdings}
              />
            )}
          </section>

          {/* Performance Chart - Show charts for each holding */}
          {holdings.length > 0 && (
            <section>
              <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
                Performance
              </h2>
              <div className="space-y-6">
                {holdings.map((holding) => (
                  <div
                    key={holding.ticker}
                    className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800"
                  >
                    <PriceChart ticker={holding.ticker} initialTimeRange="1M" />
                  </div>
                ))}
              </div>
            </section>
          )}

          {/* Holdings */}
          <section>
            <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
              Holdings
            </h2>
            <HoldingsTable
              holdings={holdings}
              holdingsDTO={holdingsData?.holdings}
              isLoading={holdingsLoading}
              onQuickSell={handleQuickSell}
            />
          </section>

          {/* Transaction History */}
          <section>
            <h2 className="mb-4 text-2xl font-semibold text-gray-900 dark:text-white">
              Transaction History
            </h2>
            <TransactionList
              transactions={transactions}
              isLoading={transactionsLoading}
            />
          </section>
        </div>

        {/* Sidebar */}
        <div className="space-y-8 lg:col-span-1">
          {/* Trade Form */}
          <section ref={tradeFormRef}>
            <TradeForm
              onSubmit={handleTradeSubmit}
              isSubmitting={executeTrade.isPending}
              holdings={holdings}
              quickSellData={quickSellData}
            />
          </section>
        </div>
      </div>
    </div>
  )
}
