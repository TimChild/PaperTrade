import { useMemo } from 'react'
import type { Holding } from '@/types/portfolio'
import type { HoldingDTO } from '@/services/api/types'
import { formatCurrency, formatPercent, formatNumber } from '@/utils/formatters'
import { useBatchPricesQuery } from '@/hooks/usePriceQuery'

interface HoldingsTableProps {
  holdings: Holding[]
  holdingsDTO?: HoldingDTO[] // Raw backend DTOs for ticker extraction
  isLoading?: boolean
}

export function HoldingsTable({
  holdings,
  holdingsDTO,
  isLoading = false,
}: HoldingsTableProps): React.JSX.Element {
  // Extract tickers from holdings
  const tickers = useMemo(() => {
    if (holdingsDTO && holdingsDTO.length > 0) {
      return holdingsDTO.map((h) => h.ticker)
    }
    return holdings.map((h) => h.ticker)
  }, [holdings, holdingsDTO])

  // Fetch real-time prices
  const {
    data: priceMap,
    isLoading: pricesLoading,
    isError: pricesError,
  } = useBatchPricesQuery(tickers)

  // Calculate holdings with real prices
  const holdingsWithRealPrices = useMemo(() => {
    if (!priceMap || priceMap.size === 0) {
      return holdings
    }

    return holdings.map((holding) => {
      const price = priceMap.get(holding.ticker)
      if (!price) {
        return holding
      }

      const currentPrice = price.price.amount
      const marketValue = currentPrice * holding.quantity
      const costBasis = holding.averageCost * holding.quantity
      const gainLoss = marketValue - costBasis
      const gainLossPercent = (gainLoss / costBasis) * 100

      return {
        ...holding,
        currentPrice,
        marketValue,
        gainLoss,
        gainLossPercent,
      }
    })
  }, [holdings, priceMap])

  if (isLoading || pricesLoading) {
    return (
      <div className="overflow-hidden rounded-lg border border-gray-300 bg-white dark:border-gray-700 dark:bg-gray-800">
        <div className="animate-pulse p-6">
          <div className="mb-4 h-6 w-32 rounded bg-gray-300 dark:bg-gray-700"></div>
          <div className="space-y-3">
            {[1, 2, 3].map((i) => (
              <div key={i} className="h-12 rounded bg-gray-300 dark:bg-gray-700"></div>
            ))}
          </div>
        </div>
      </div>
    )
  }

  if (holdingsWithRealPrices.length === 0) {
    return (
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <p className="text-center text-gray-600 dark:text-gray-400">
          No holdings in this portfolio yet
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-lg border border-gray-300 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <div className="overflow-x-auto">
        <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
          <thead className="bg-gray-50 dark:bg-gray-900">
            <tr>
              <th
                scope="col"
                className="px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-gray-700 dark:text-gray-300"
              >
                Symbol
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-700 dark:text-gray-300"
              >
                Shares
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-700 dark:text-gray-300"
              >
                Avg Cost
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-700 dark:text-gray-300"
              >
                Current Price
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-700 dark:text-gray-300"
              >
                Market Value
              </th>
              <th
                scope="col"
                className="px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-gray-700 dark:text-gray-300"
              >
                Gain/Loss
              </th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200 bg-white dark:divide-gray-700 dark:bg-gray-800">
            {holdingsWithRealPrices.map((holding) => {
              const isPositive = holding.gainLoss >= 0
              const gainLossColorClass = isPositive
                ? 'text-positive dark:text-positive-light'
                : 'text-negative dark:text-negative-light'

              // Check if price is from API or mock
              const priceFromAPI = priceMap?.has(holding.ticker)

              return (
                <tr
                  key={holding.ticker}
                  className="hover:bg-gray-50 dark:hover:bg-gray-700/50"
                >
                  <td className="whitespace-nowrap px-6 py-4 text-sm font-medium text-gray-900 dark:text-white">
                    {holding.ticker}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-700 dark:text-gray-300">
                    {formatNumber(holding.quantity, 0)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-700 dark:text-gray-300">
                    {formatCurrency(holding.averageCost)}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm text-gray-700 dark:text-gray-300">
                    {pricesError && !priceFromAPI ? (
                      <span className="text-red-600 dark:text-red-400">N/A</span>
                    ) : (
                      formatCurrency(holding.currentPrice)
                    )}
                  </td>
                  <td className="whitespace-nowrap px-6 py-4 text-right text-sm font-medium text-gray-900 dark:text-white">
                    {formatCurrency(holding.marketValue)}
                  </td>
                  <td
                    className={`whitespace-nowrap px-6 py-4 text-right text-sm font-medium ${gainLossColorClass}`}
                  >
                    <div>
                      {isPositive ? '+' : ''}
                      {formatCurrency(holding.gainLoss)}
                    </div>
                    <div className="text-xs">({formatPercent(holding.gainLossPercent)})</div>
                  </td>
                </tr>
              )
            })}
          </tbody>
        </table>
      </div>
    </div>
  )
}
