import type { Portfolio } from '@/types/portfolio'
import {
  formatCurrency,
  formatPercent,
  formatClockTime,
} from '@/utils/formatters'
import { MetricStat } from '@/components/ui/MetricStat'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { Caption } from '@/components/ui/Caption'
import { Skeleton } from '@/components/ui/skeleton'

interface PortfolioHeroProps {
  portfolio: Portfolio | null
  /** Epoch ms — when the data we're showing was last refetched. */
  lastUpdatedAt: number | undefined
  isLoading: boolean
  className?: string
}

/**
 * Editorial hero band for PortfolioDetail.
 *
 * Total value gets the largest display-serif number on the page (`hero`
 * size). Daily change sits beside it as a secondary metric. Cash + holdings
 * value live below in muted tabular form. A "Last updated" caption ties
 * everything to a clock time so the reader knows the data's freshness
 * (PR #246 surfacing).
 *
 * The hero deliberately does NOT live inside a card — it sits flat against
 * the canvas, separated from the rest of the page by generous whitespace
 * and a hairline rule. That's the editorial move: numbers carry the
 * composition, not card chrome.
 */
export function PortfolioHero({
  portfolio,
  lastUpdatedAt,
  isLoading,
  className,
}: PortfolioHeroProps): React.JSX.Element {
  if (isLoading || !portfolio) {
    return (
      <div className={className}>
        <Skeleton className="h-3 w-24 mb-3" />
        <Skeleton className="h-16 w-72 mb-4" />
        <Skeleton className="h-5 w-40 mb-6" />
        <div className="flex gap-12">
          <Skeleton className="h-9 w-28" />
          <Skeleton className="h-9 w-28" />
        </div>
      </div>
    )
  }

  const isPositive = portfolio.dailyChange >= 0
  const dailyChangeTone: 'gain' | 'loss' = isPositive ? 'gain' : 'loss'
  const sign = isPositive ? '+' : ''

  const holdingsValue = portfolio.totalValue - portfolio.cashBalance

  return (
    <section
      className={className}
      aria-labelledby="portfolio-hero-label"
      data-testid="portfolio-hero"
    >
      {/* Hero metric — total value. The single most important number on
          the page. */}
      <div className="reveal" style={{ ['--reveal-delay' as string]: '120ms' }}>
        <MetricStat
          label="Total value"
          value={formatCurrency(portfolio.totalValue)}
          delta={{
            value: `${sign}${formatCurrency(portfolio.dailyChange)}`,
            tone: dailyChangeTone,
            secondary: formatPercent(portfolio.dailyChangePercent),
          }}
          caption={
            <Caption data-testid="portfolio-last-updated">
              Last updated · {formatClockTime(lastUpdatedAt)}
            </Caption>
          }
          size="hero"
          testId="portfolio-total-value"
        />
        {/* Hidden semantic ID for the screen-reader label */}
        <span id="portfolio-hero-label" className="sr-only">
          Portfolio summary for {portfolio.name}, total value{' '}
          {formatCurrency(portfolio.totalValue)}
        </span>
        {/*
          Mirror the legacy testids that other parts of the app (and the
          existing test suite) depend on. Keeps the hero composable while
          preserving the contract.
        */}
        <span
          data-testid="portfolio-daily-change"
          className="sr-only"
        >{`${sign}${formatCurrency(portfolio.dailyChange)}`}</span>
        <span data-testid="portfolio-daily-change-percent" className="sr-only">
          {formatPercent(portfolio.dailyChangePercent)}
        </span>
      </div>

      {/* Secondary stats row — cash and holdings, in tabular mono. Sits below
          the hero with generous whitespace so the hero stays the moment. */}
      <div
        className="mt-8 grid grid-cols-2 gap-6 sm:gap-12 sm:flex sm:flex-row reveal"
        style={{ ['--reveal-delay' as string]: '220ms' }}
      >
        <div className="flex flex-col gap-1">
          <Eyebrow>Cash</Eyebrow>
          <p
            className="font-tabular text-body-md text-ink"
            data-testid="portfolio-cash-balance"
          >
            {formatCurrency(portfolio.cashBalance)}
          </p>
        </div>

        {holdingsValue > 0 && (
          <div
            className="flex flex-col gap-1"
            data-testid="portfolio-holdings-value"
          >
            <Eyebrow>Holdings</Eyebrow>
            <p className="font-tabular text-body-md text-ink">
              {formatCurrency(holdingsValue)}
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
