import { useParams, Link } from 'react-router-dom'
import { useRef, useState } from 'react'
import { ArrowLeft, ArrowUpRight } from 'lucide-react'
import {
  usePortfolio,
  usePortfolioBalance,
  useExecuteTrade,
} from '@/hooks/usePortfolio'
import { useHoldings } from '@/hooks/useHoldings'
import { useTransactions } from '@/hooks/useTransactions'
import { HoldingsTable } from '@/components/features/portfolio/HoldingsTable'
import { TransactionList } from '@/components/features/portfolio/TransactionList'
import { TradeForm } from '@/components/features/portfolio/TradeForm'
import { LightweightPriceChart } from '@/components/features/PriceChart'
import { PortfolioHero } from '@/components/features/portfolio/PortfolioHero'
import { PortfolioDetailSkeleton } from '@/components/features/portfolio/PortfolioDetailSkeleton'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { SectionHeader } from '@/components/ui/SectionHeader'
import {
  adaptPortfolio,
  adaptHolding,
  adaptTransaction,
} from '@/utils/adapters'
import { formatTradeError } from '@/utils/errorFormatters'
import { toasts } from '@/utils/toast'
import type { TradeRequest } from '@/services/api/types'

/**
 * PortfolioDetail — Wave 1 lighthouse for the editorial dark theme.
 *
 * Layout philosophy:
 *   - The page is composed as an editorial document, not a dashboard. The
 *     hero (total value) is the strongest moment and gets the largest
 *     display-serif number on the page.
 *   - Sections are separated by generous whitespace and hairline rules,
 *     not card chrome. Holdings live in a hairline-bordered table; the
 *     trade form sits in a flush panel; transactions in another.
 *   - A single staggered page-load reveal cascades from the eyebrow → hero
 *     number → secondary stats → main content. We do NOT animate hover
 *     states or per-cell transitions; the editorial mood is "considered",
 *     not "kinetic".
 */
export function PortfolioDetail(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const portfolioId = id || ''
  const tradeFormRef = useRef<HTMLElement>(null)
  const [quickSellState, setQuickSellState] = useState<{
    action: 'BUY' | 'SELL'
    ticker: string
    quantity: string
    date: string
  }>({ action: 'BUY', ticker: '', quantity: '', date: '' })

  const {
    data: portfolioDTO,
    isLoading: portfolioLoading,
    isError,
    error,
  } = usePortfolio(portfolioId)
  const {
    data: balanceData,
    isLoading: balanceLoading,
    dataUpdatedAt: balanceUpdatedAt,
  } = usePortfolioBalance(portfolioId)
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
  const transactions = transactionsData?.items.map(adaptTransaction) || []

  const handleTradeSubmit = (trade: TradeRequest) => {
    console.log(
      `[TradeSubmit] Portfolio ID: ${portfolioId}, Action: ${trade.action}, Ticker: ${trade.ticker}, Quantity: ${trade.quantity}`
    )
    executeTrade.mutate(trade, {
      onSuccess: () => {
        // Show success toast with trade details
        const quantity = parseFloat(trade.quantity)
        if (trade.action === 'BUY') {
          toasts.tradeBuy(trade.ticker, quantity)
        } else {
          toasts.tradeSell(trade.ticker, quantity)
        }
        // Reset quick sell state
        setQuickSellState({ action: 'BUY', ticker: '', quantity: '', date: '' })
      },
      onError: (error) => {
        console.error(`[TradeSubmit Error] Portfolio ID: ${portfolioId}`, error)
        const errorMessage = formatTradeError(error)
        toasts.tradeError(errorMessage)
      },
    })
  }

  const handleQuickSell = (ticker: string, quantity: number) => {
    setQuickSellState({
      action: 'SELL',
      ticker,
      quantity: quantity.toString(),
      date: '',
    })
    setTimeout(() => {
      tradeFormRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      })
    }, 100)
  }

  const handleChartClick = (data: {
    ticker: string
    date: string
    price?: number
  }) => {
    const today = new Date().toISOString().split('T')[0]
    const isHistorical = data.date !== today

    setQuickSellState({
      action: 'BUY',
      ticker: data.ticker,
      quantity: '',
      date: isHistorical ? data.date : '',
    })

    setTimeout(() => {
      tradeFormRef.current?.scrollIntoView({
        behavior: 'smooth',
        block: 'nearest',
      })
    }, 100)
  }

  if (isError) {
    return (
      <PageFrame>
        <ErrorDisplay error={error} />
        <Link
          to="/dashboard"
          className="mt-4 inline-flex items-center gap-1.5 text-amber hover:text-amber-hover text-body-sm"
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Back to Dashboard
        </Link>
      </PageFrame>
    )
  }

  if (portfolioLoading) {
    return (
      <PageFrame>
        <PortfolioDetailSkeleton />
      </PageFrame>
    )
  }

  return (
    <PageFrame>
      {/* ─── Top nav row ─── */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
      >
        <Link
          to="/dashboard"
          data-testid="portfolio-detail-back-link"
          className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink text-body-sm transition-colors"
          style={{ minHeight: 'auto' }}
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Dashboard
        </Link>
        <Link
          to={`/portfolio/${portfolioId}/analytics`}
          data-testid="analytics-tab"
          className="inline-flex items-center gap-1.5 border border-hairline-strong rounded-editorial px-3 py-2 text-body-sm text-ink hover:border-amber hover:text-amber transition-colors"
          style={{ minHeight: 'auto' }}
        >
          Analytics
          <ArrowUpRight className="h-3.5 w-3.5" />
        </Link>
      </div>

      {/* ─── Editorial header (eyebrow + name) ─── */}
      <header
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '60ms' }}
      >
        <Eyebrow>Portfolio</Eyebrow>
        <h1
          className="font-display text-display-md sm:text-display-lg tracking-tight text-ink mt-1"
          data-testid="portfolio-detail-name"
        >
          {portfolio?.name || 'Portfolio Details'}
        </h1>
      </header>

      {/* ─── Hairline rule under the header — separates header from data ─── */}
      <div
        className="mt-6 sm:mt-8 border-t border-hairline reveal"
        style={{ ['--reveal-delay' as string]: '90ms' }}
      />

      {/* ─── Hero band: total value + daily change + cash + holdings ─── */}
      <div className="mt-6 sm:mt-8">
        <PortfolioHero
          portfolio={portfolio}
          lastUpdatedAt={balanceUpdatedAt}
          isLoading={balanceLoading || !portfolio}
        />
      </div>

      {/* ─── Hairline divider before the main grid ─── */}
      <div
        className="mt-10 sm:mt-12 border-t border-hairline reveal"
        style={{ ['--reveal-delay' as string]: '300ms' }}
      />

      {/* ─── Two-column grid: data on the left, trade rail on the right ─── */}
      <div className="mt-6 sm:mt-10 grid gap-10 lg:gap-14 grid-cols-1 lg:grid-cols-[minmax(0,1fr)_360px]">
        <div className="space-y-12 sm:space-y-16 min-w-0">
          {/* Holdings */}
          <section
            className="reveal"
            style={{ ['--reveal-delay' as string]: '360ms' }}
          >
            <SectionHeader
              eyebrow="Positions"
              title="Holdings"
              size="sm"
              description={
                holdings.length > 0
                  ? `${holdings.length} active position${holdings.length === 1 ? '' : 's'}.`
                  : undefined
              }
            />
            <HoldingsTable
              holdings={holdings}
              holdingsDTO={holdingsData?.holdings}
              isLoading={holdingsLoading}
              onQuickSell={handleQuickSell}
            />
          </section>

          {/* Performance — chart for each holding */}
          {holdings.length > 0 && (
            <section
              className="reveal"
              style={{ ['--reveal-delay' as string]: '420ms' }}
            >
              <SectionHeader
                eyebrow="Trajectory"
                title="Performance"
                size="sm"
                description="Trade markers overlay each chart. Click any point to seed a new trade."
              />
              <div className="space-y-8">
                {holdings.map((holding) => (
                  <LightweightPriceChart
                    key={holding.ticker}
                    ticker={holding.ticker}
                    portfolioId={portfolioId}
                    onChartClick={handleChartClick}
                  />
                ))}
              </div>
            </section>
          )}

          {/* Transactions */}
          <section
            className="reveal"
            style={{ ['--reveal-delay' as string]: '480ms' }}
          >
            <SectionHeader
              eyebrow="Ledger"
              title="Transaction history"
              size="sm"
            />
            <TransactionList
              transactions={transactions}
              isLoading={transactionsLoading}
              showSearch={true}
            />
          </section>
        </div>

        {/* Trade rail */}
        <aside
          className="reveal"
          style={{ ['--reveal-delay' as string]: '420ms' }}
        >
          <section ref={tradeFormRef} className="lg:sticky lg:top-6">
            <SectionHeader eyebrow="New trade" title="Place order" size="sm" />
            <TradeForm
              key={`${quickSellState.action}-${quickSellState.ticker}-${quickSellState.quantity}-${quickSellState.date}`}
              onSubmit={handleTradeSubmit}
              isSubmitting={executeTrade.isPending}
              holdings={holdings}
              initialAction={quickSellState.action}
              initialTicker={quickSellState.ticker}
              initialQuantity={quickSellState.quantity}
              initialDate={quickSellState.date}
            />
          </section>
        </aside>
      </div>
    </PageFrame>
  )
}

/**
 * PageFrame — the editorial outer wrapper. Generous side gutters, max
 * width that prevents lines of body text from getting too long but lets
 * the holdings table stretch when there are many columns.
 */
function PageFrame({
  children,
}: {
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="min-h-screen bg-canvas">
      <div className="mx-auto max-w-[1240px] px-5 sm:px-8 lg:px-12 py-8 sm:py-12 lg:py-16">
        {children}
      </div>
    </div>
  )
}
