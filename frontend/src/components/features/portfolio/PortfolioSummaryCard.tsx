import type { Portfolio } from '@/types/portfolio'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { useExtendedLoadingFlag } from '@/hooks/useExtendedLoadingFlag'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

interface PortfolioSummaryCardProps {
  portfolio: Portfolio
  isLoading?: boolean
  /**
   * Phase J / Task #214 — pricing availability discriminator. When
   * ``"loading"`` total-value + daily-change render as a skeleton;
   * cash remains visible. When ``"unavailable"`` the retry budget is
   * exhausted and an error block surfaces the stuck tickers.
   */
  pricingStatus?: 'ok' | 'loading' | 'unavailable'
  missingTickers?: string[]
}

/**
 * Format the `balanceAsOf` ISO timestamp for the "Last updated" caption.
 * Returns `null` when no timestamp is available (don't render the caption).
 */
function formatLastUpdated(isoString: string | undefined): string | null {
  if (!isoString) return null
  const parsed = new Date(isoString)
  if (Number.isNaN(parsed.getTime())) return null
  return new Intl.DateTimeFormat('en-US', {
    hour: 'numeric',
    minute: '2-digit',
    second: '2-digit',
    hour12: true,
  }).format(parsed)
}

/**
 * Editorial portfolio summary card — flush hairline panel pairing a
 * display-serif total value with day-change delta and a cash/holdings row.
 *
 * Lives in any context that benefits from a self-contained portfolio
 * summary (currently retained as a building block; the Dashboard now uses
 * `PortfolioCard` directly).
 */
export function PortfolioSummaryCard({
  portfolio,
  isLoading = false,
  pricingStatus = 'ok',
  missingTickers = [],
}: PortfolioSummaryCardProps): React.JSX.Element {
  const totalValue = portfolio.totalValue
  const holdingsValue = portfolio.totalValue - portfolio.cashBalance
  const lastUpdated = formatLastUpdated(portfolio.balanceAsOf)

  const isPricingLoading = pricingStatus === 'loading'
  const isPricingUnavailable = pricingStatus === 'unavailable'
  const showExtendedCaption = useExtendedLoadingFlag(isPricingLoading)

  if (isLoading) {
    return (
      <div className="rounded-editorial border border-hairline bg-canvas-raised/40 p-6 space-y-4">
        <Skeleton className="h-6 w-48" />
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-6 w-32" />
      </div>
    )
  }

  const isPositiveChange = portfolio.dailyChange >= 0
  const changeColorClass = isPositiveChange ? 'text-gain' : 'text-loss'
  const sign = isPositiveChange ? '+' : ''

  return (
    <article className="rounded-editorial border border-hairline bg-canvas-raised/40 p-6">
      <header className="mb-4">
        <Eyebrow>Portfolio</Eyebrow>
        <h3 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
          {portfolio.name}
        </h3>
      </header>

      <div className="space-y-4">
        <div>
          <Eyebrow>Total value</Eyebrow>
          {isPricingLoading ? (
            <div className="mt-1 space-y-2">
              <Skeleton className="h-10 w-48" />
              {showExtendedCaption && (
                <p
                  className="font-caption text-ink-muted"
                  data-testid="portfolio-summary-loading-caption"
                >
                  Fetching market data…
                </p>
              )}
            </div>
          ) : isPricingUnavailable ? (
            <div
              className="mt-1 rounded-editorial border border-hairline bg-loss-soft/30 p-3"
              data-testid="portfolio-summary-pricing-unavailable"
            >
              <p className="font-tabular text-body-sm text-ink">
                Market data unavailable
              </p>
              {missingTickers.length > 0 && (
                <p className="font-caption text-ink-muted mt-1">
                  {missingTickers.join(', ')}
                </p>
              )}
            </div>
          ) : (
            <>
              <p
                className="mt-1 font-display-numeric tabular-nums text-display-md text-ink"
                data-testid="portfolio-total-value"
              >
                {formatCurrency(totalValue)}
              </p>
              {lastUpdated && (
                <p
                  className="font-caption mt-2"
                  data-testid="portfolio-last-updated"
                >
                  Last updated · {lastUpdated}
                </p>
              )}
            </>
          )}
        </div>

        <div>
          <Eyebrow>Daily change</Eyebrow>
          {isPricingLoading || isPricingUnavailable ? (
            <div className="mt-1">
              <Skeleton className="h-5 w-32" />
            </div>
          ) : (
            <div className="mt-1 flex flex-wrap items-baseline gap-x-2 font-tabular text-body-md">
              <p
                className={cn(changeColorClass)}
                data-testid="portfolio-daily-change"
              >
                {sign}
                {formatCurrency(portfolio.dailyChange)}
              </p>
              <p
                className={cn(changeColorClass, 'text-body-sm')}
                data-testid="portfolio-daily-change-percent"
              >
                ({formatPercent(portfolio.dailyChangePercent)})
              </p>
            </div>
          )}
        </div>

        <div className="border-t border-hairline pt-4 space-y-2">
          <div className="flex justify-between font-tabular text-body-sm">
            <span className="font-eyebrow text-ink-muted not-italic tracking-eyebrow">
              Cash balance
            </span>
            <span className="text-ink" data-testid="portfolio-cash-balance">
              {formatCurrency(portfolio.cashBalance)}
            </span>
          </div>
          {holdingsValue > 0 && (
            <div className="flex justify-between font-tabular text-body-sm">
              <span className="font-eyebrow text-ink-muted not-italic tracking-eyebrow">
                Holdings value
              </span>
              <span className="text-ink">{formatCurrency(holdingsValue)}</span>
            </div>
          )}
        </div>
      </div>
    </article>
  )
}
