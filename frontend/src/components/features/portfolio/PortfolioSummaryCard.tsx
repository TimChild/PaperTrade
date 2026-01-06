import { useMemo } from 'react'
import type { Portfolio } from '@/types/portfolio'
import type { HoldingDTO } from '@/services/api/types'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { useBatchPricesQuery, usePriceStaleness } from '@/hooks/usePriceQuery'

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
  const { data: priceMap, isLoading: pricesLoading } = useBatchPricesQuery(tickers)

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
      return new Date(current.timestamp) < new Date(oldest.timestamp) ? current : oldest
    }, prices[0])
  }, [priceMap])

  const staleness = usePriceStaleness(stalestPrice ?? undefined)

  if (isLoading || pricesLoading) {
    return (
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-48 rounded bg-gray-300 dark:bg-gray-700"></div>
          <div className="h-10 w-64 rounded bg-gray-300 dark:bg-gray-700"></div>
          <div className="h-6 w-32 rounded bg-gray-300 dark:bg-gray-700"></div>
        </div>
      </div>
    )
  }

  const isPositiveChange = portfolio.dailyChange >= 0
  const changeColorClass = isPositiveChange
    ? 'text-positive dark:text-positive-light'
    : 'text-negative dark:text-negative-light'

  return (
    <div className="rounded-lg border border-gray-300 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="mb-4">
        <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
          {portfolio.name}
        </h2>
      </div>

      <div className="space-y-4">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">Total Value</p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white" data-testid="portfolio-total-value">
            {formatCurrency(totalValue)}
          </p>
          {staleness && (
            <p className="text-xs text-gray-500 dark:text-gray-400">
              Updated {staleness}
            </p>
          )}
        </div>

        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">Daily Change</p>
          <div className="flex items-baseline gap-2">
            <p className={`text-xl font-semibold ${changeColorClass}`} data-testid="portfolio-daily-change">
              {isPositiveChange ? '+' : ''}
              {formatCurrency(portfolio.dailyChange)}
            </p>
            <p className={`text-lg font-medium ${changeColorClass}`} data-testid="portfolio-daily-change-percent">
              ({formatPercent(portfolio.dailyChangePercent)})
            </p>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-4 dark:border-gray-700">
          <div className="flex justify-between">
            <p className="text-sm text-gray-600 dark:text-gray-400">Cash Balance</p>
            <p className="text-sm font-medium text-gray-900 dark:text-white" data-testid="portfolio-cash-balance">
              {formatCurrency(portfolio.cashBalance)}
            </p>
          </div>
          {holdingsValue > 0 && (
            <div className="mt-2 flex justify-between">
              <p className="text-sm text-gray-600 dark:text-gray-400">Holdings Value</p>
              <p className="text-sm font-medium text-gray-900 dark:text-white">
                {formatCurrency(holdingsValue)}
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
