import { useParams, Link } from 'react-router-dom'
import { useRef, useState } from 'react'
import toast from 'react-hot-toast'
import {
  usePortfolio,
  usePortfolioBalance,
  useExecuteTrade,
} from '@/hooks/usePortfolio'
import { useHoldings } from '@/hooks/useHoldings'
import { useTransactions } from '@/hooks/useTransactions'
import { PortfolioSummaryCard } from '@/components/features/portfolio/PortfolioSummaryCard'
import { HoldingsTable } from '@/components/features/portfolio/HoldingsTable'
import { TransactionList } from '@/components/features/portfolio/TransactionList'
import { TradeForm } from '@/components/features/portfolio/TradeForm'
import { PriceChart } from '@/components/features/PriceChart'
import { PortfolioDetailSkeleton } from '@/components/features/portfolio/PortfolioDetailSkeleton'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'
import {
  adaptPortfolio,
  adaptHolding,
  adaptTransaction,
} from '@/utils/adapters'
import { formatTradeError } from '@/utils/errorFormatters'
import type { TradeRequest } from '@/services/api/types'

export function PortfolioDetail(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const portfolioId = id || ''
  const tradeFormRef = useRef<HTMLElement>(null)
  const [quickSellState, setQuickSellState] = useState<{
    action: 'BUY' | 'SELL'
    ticker: string
    quantity: string
  }>({ action: 'BUY', ticker: '', quantity: '' })

  const {
    data: portfolioDTO,
    isLoading: portfolioLoading,
    isError,
    error,
  } = usePortfolio(portfolioId)
  const { data: balanceData, isLoading: balanceLoading } =
    usePortfolioBalance(portfolioId)
  const { data: holdingsData, isLoading: holdingsLoading } =
    useHoldings(portfolioId)
  const { data: transactionsData, isLoading: transactionsLoading } =
    useTransactions(portfolioId)
  const executeTrade = useExecuteTrade(portfolioId)

  // Adapt backend DTOs to frontend types
  const portfolio = portfolioDTO
    ? adaptPortfolio(portfolioDTO, balanceData || null)
    : null
  const holdings = holdingsData?.holdings.map(adaptHolding) || []
  const transactions =
    transactionsData?.transactions.map(adaptTransaction) || []

  const handleTradeSubmit = (trade: TradeRequest) => {
    console.log(
      `[TradeSubmit] Portfolio ID: ${portfolioId}, Action: ${trade.action}, Ticker: ${trade.ticker}, Quantity: ${trade.quantity}`
    )
    executeTrade.mutate(trade, {
      onSuccess: () => {
        // Show success toast with trade details
        const action = trade.action === 'BUY' ? 'Bought' : 'Sold'
        const quantity = parseFloat(trade.quantity)
        toast.success(
          `${action} ${quantity} ${quantity === 1 ? 'share' : 'shares'} of ${trade.ticker}`
        )
        // Reset quick sell state
        setQuickSellState({ action: 'BUY', ticker: '', quantity: '' })
      },
      onError: (error) => {
        console.error(`[TradeSubmit Error] Portfolio ID: ${portfolioId}`, error)
        const errorMessage = formatTradeError(error)
        toast.error(errorMessage)
      },
    })
  }

  const handleQuickSell = (ticker: string, quantity: number) => {
    // Set quick sell state
    setQuickSellState({
      action: 'SELL',
      ticker,
      quantity: quantity.toString(),
    })

    // Scroll to trade form with smooth behavior
    setTimeout(() => {
      tradeFormRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      })
    }, 100)
  }

  if (isError) {
    return (
      <div className="min-h-screen bg-background-primary px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
        <div className="max-w-screen-2xl mx-auto">
          <ErrorDisplay error={error} />
          <Link
            to="/dashboard"
            className="mt-4 inline-block text-primary hover:underline text-sm sm:text-base"
          >
            ← Back to Dashboard
          </Link>
        </div>
      </div>
    )
  }

  if (portfolioLoading) {
    return (
      <div className="min-h-screen bg-background-primary px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
        <div className="max-w-screen-2xl mx-auto">
          <PortfolioDetailSkeleton />
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background-primary px-4 sm:px-6 lg:px-8 py-6 sm:py-8 lg:py-12">
      <div className="max-w-screen-2xl mx-auto">
        {/* Header with navigation */}
        <div className="mb-6 sm:mb-8">
          <Link
            to="/dashboard"
            data-testid="portfolio-detail-back-link"
            className="mb-3 sm:mb-4 inline-flex items-center text-primary hover:underline text-sm sm:text-base"
          >
            ← Back to Dashboard
          </Link>
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 sm:gap-4">
            <h1
              className="text-2xl sm:text-3xl lg:text-heading-xl text-foreground-primary"
              data-testid="portfolio-detail-name"
            >
              {portfolio?.name || 'Portfolio Details'}
            </h1>
            <Link
              to={`/portfolio/${portfolioId}/analytics`}
              data-testid="analytics-tab"
              className="inline-flex items-center justify-center rounded-button bg-primary text-white px-4 py-2.5 hover:bg-primary-hover shadow-card transition-colors text-sm sm:text-base w-full sm:w-auto"
            >
              View Analytics
            </Link>
          </div>
        </div>

        <div className="grid gap-4 sm:gap-6 lg:gap-card-gap grid-cols-1 lg:grid-cols-3">
          {/* Main Content */}
          <div className="space-y-4 sm:space-y-6 lg:space-y-card-gap lg:col-span-2">
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
                <h2 className="mb-3 sm:mb-4 text-lg sm:text-xl lg:text-heading-lg text-foreground-primary">
                  Performance
                </h2>
                <div className="space-y-4 sm:space-y-6 lg:space-y-card-gap">
                  {holdings.map((holding) => (
                    <PriceChart
                      key={holding.ticker}
                      ticker={holding.ticker}
                      initialTimeRange="1M"
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Holdings */}
            <section>
              <h2 className="mb-3 sm:mb-4 text-lg sm:text-xl lg:text-heading-lg text-foreground-primary">
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
              <h2 className="mb-3 sm:mb-4 text-lg sm:text-xl lg:text-heading-lg text-foreground-primary">
                Transaction History
              </h2>
              <TransactionList
                transactions={transactions}
                isLoading={transactionsLoading}
                showSearch={true}
              />
            </section>
          </div>

          {/* Sidebar */}
          <div className="space-y-4 sm:space-y-6 lg:space-y-card-gap lg:col-span-1">
            {/* Trade Form */}
            <section ref={tradeFormRef}>
              <TradeForm
                key={`${quickSellState.action}-${quickSellState.ticker}-${quickSellState.quantity}`}
                onSubmit={handleTradeSubmit}
                isSubmitting={executeTrade.isPending}
                holdings={holdings}
                initialAction={quickSellState.action}
                initialTicker={quickSellState.ticker}
                initialQuantity={quickSellState.quantity}
              />
            </section>
          </div>
        </div>
      </div>
    </div>
  )
}
