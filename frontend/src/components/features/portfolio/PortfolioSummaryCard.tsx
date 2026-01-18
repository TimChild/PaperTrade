import { useMemo } from 'react'
import type { Portfolio } from '@/types/portfolio'
import type { HoldingDTO } from '@/services/api/types'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { useBatchPricesQuery, usePriceStaleness } from '@/hooks/usePriceQuery'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

interface PortfolioSummaryCardProps {
  portfolio: Portfolio
  holdingsDTO?: HoldingDTO[] // Raw backend DTOs for ticker extraction
  isLoading?: boolean
}

export function PortfolioSummaryCard({
  portfolio,
  holdingsDTO,
  isLoading = false,
}: PortfolioSummaryCardProps): React.JSX.Element {
  // Extract tickers from holdings
  const tickers = useMemo(() => {
    return holdingsDTO ? holdingsDTO.map((h) => h.ticker) : []
  }, [holdingsDTO])

  // Fetch real-time prices
  const { data: priceMap, isLoading: pricesLoading } =
    useBatchPricesQuery(tickers)

  // Calculate total portfolio value with real prices
  const { totalValue, holdingsValue } = useMemo(() => {
    if (!priceMap || !holdingsDTO || holdingsDTO.length === 0) {
      return { totalValue: portfolio.cashBalance, holdingsValue: 0 }
    }

    const holdingsVal = holdingsDTO.reduce((sum, holding) => {
      const price = priceMap.get(holding.ticker)
      if (!price) return sum
      return sum + price.price.amount * parseFloat(holding.quantity)
    }, 0)

    return {
      totalValue: portfolio.cashBalance + holdingsVal,
      holdingsValue: holdingsVal,
    }
  }, [portfolio.cashBalance, holdingsDTO, priceMap])

  // Determine most stale price (for indicator)
  const stalestPrice = useMemo(() => {
    if (!priceMap || priceMap.size === 0) return null

    const prices = Array.from(priceMap.values())
    return prices.reduce((oldest, current) => {
      return new Date(current.timestamp) < new Date(oldest.timestamp)
        ? current
        : oldest
    }, prices[0])
  }, [priceMap])

  const staleness = usePriceStaleness(stalestPrice ?? undefined)

  if (isLoading || pricesLoading) {
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
        <CardTitle className="text-lg sm:text-xl lg:text-heading-md">{portfolio.name}</CardTitle>
      </CardHeader>

      <CardContent className="space-y-3 sm:space-y-4">
        <div>
          <p className="text-xs sm:text-sm text-foreground-secondary">Total Value</p>
          <p
            className="text-xl sm:text-2xl lg:text-value-primary text-foreground-primary"
            data-testid="portfolio-total-value"
          >
            {formatCurrency(totalValue)}
          </p>
          {staleness && (
            <p className="text-xs text-foreground-tertiary">
              Updated {staleness}
            </p>
          )}
        </div>

        <div>
          <p className="text-xs sm:text-sm text-foreground-secondary">Daily Change</p>
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
            <p className="text-xs sm:text-sm text-foreground-secondary">Cash Balance</p>
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
