import type { Portfolio } from '@/types/portfolio'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

interface PortfolioSummaryCardProps {
  portfolio: Portfolio
  isLoading?: boolean
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

export function PortfolioSummaryCard({
  portfolio,
  isLoading = false,
}: PortfolioSummaryCardProps): React.JSX.Element {
  // Use backend-calculated total value (already accounts for weekends/holidays)
  const totalValue = portfolio.totalValue
  const holdingsValue = portfolio.totalValue - portfolio.cashBalance
  const lastUpdated = formatLastUpdated(portfolio.balanceAsOf)

  if (isLoading) {
    return (
      <Card>
        <CardContent className="space-y-4 pt-6">
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-10 w-64" />
          <Skeleton className="h-6 w-32" />
        </CardContent>
      </Card>
    )
  }

  const isPositiveChange = portfolio.dailyChange >= 0
  const changeColorClass = isPositiveChange ? 'text-positive' : 'text-negative'

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg sm:text-xl lg:text-heading-md">
          {portfolio.name}
        </CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 sm:space-y-4">
        <div>
          <p className="text-xs sm:text-sm text-foreground-secondary">
            Total Value
          </p>
          <p
            className="text-xl sm:text-2xl lg:text-value-primary text-foreground-primary"
            data-testid="portfolio-total-value"
          >
            {formatCurrency(totalValue)}
          </p>
          {lastUpdated && (
            <p
              className="text-xs text-foreground-tertiary mt-1"
              data-testid="portfolio-last-updated"
            >
              Last updated: {lastUpdated}
            </p>
          )}
        </div>

        <div>
          <p className="text-xs sm:text-sm text-foreground-secondary">
            Daily Change
          </p>
          <div className="flex items-baseline gap-2">
            <p
              className={`text-base sm:text-lg lg:text-value-secondary ${changeColorClass}`}
              data-testid="portfolio-daily-change"
            >
              {isPositiveChange ? '+' : ''}
              {formatCurrency(portfolio.dailyChange)}
            </p>
            <p
              className={`text-base sm:text-lg font-medium ${changeColorClass}`}
              data-testid="portfolio-daily-change-percent"
            >
              ({formatPercent(portfolio.dailyChangePercent)})
            </p>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-3 sm:pt-4 dark:border-gray-700">
          <div className="flex justify-between">
            <p className="text-xs sm:text-sm text-foreground-secondary">
              Cash Balance
            </p>
            <p
              className="text-xs sm:text-sm font-medium text-foreground-primary"
              data-testid="portfolio-cash-balance"
            >
              {formatCurrency(portfolio.cashBalance)}
            </p>
          </div>
          {holdingsValue > 0 && (
            <div className="mt-2 flex justify-between">
              <p className="text-xs sm:text-sm text-foreground-secondary">
                Holdings Value
              </p>
              <p className="text-xs sm:text-sm font-medium text-foreground-primary">
                {formatCurrency(holdingsValue)}
              </p>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}
