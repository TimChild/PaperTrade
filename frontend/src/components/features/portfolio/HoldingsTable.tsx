import { useMemo } from 'react'
import type { Holding } from '@/types/portfolio'
import type { HoldingDTO } from '@/services/api/types'
import { formatCurrency, formatPercent, formatNumber } from '@/utils/formatters'
import { useBatchPricesQuery } from '@/hooks/usePriceQuery'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'

interface HoldingsTableProps {
  holdings: Holding[]
  holdingsDTO?: HoldingDTO[] // Raw backend DTOs for ticker extraction
  isLoading?: boolean
  onQuickSell?: (ticker: string, quantity: number) => void
}

export function HoldingsTable({
  holdings,
  holdingsDTO,
  isLoading = false,
  onQuickSell,
}: HoldingsTableProps): React.JSX.Element {
  // Extract tickers from holdings
  const tickers = useMemo(() => {
    if (holdingsDTO && holdingsDTO.length > 0) {
      return holdingsDTO.map((h) => h.ticker)
    }
    return holdings.map((h) => h.ticker)
  }, [holdings, holdingsDTO])

  // Fetch real-time prices
  const { data: priceMap, isLoading: pricesLoading } =
    useBatchPricesQuery(tickers)

  // Calculate holdings with real prices
  const holdingsWithRealPrices = useMemo(() => {
    return holdings.map((holding) => {
      const price = priceMap?.get(holding.ticker)

      // Use real-time price if available and valid, otherwise use average cost as fallback
      const currentPrice =
        price && Number.isFinite(price.price.amount)
          ? price.price.amount
          : holding.averageCost

      const marketValue = currentPrice * holding.quantity
      const costBasis = holding.averageCost * holding.quantity
      const gainLoss = marketValue - costBasis
      const gainLossPercent = costBasis !== 0 ? (gainLoss / costBasis) * 100 : 0

      return {
        ...holding,
        currentPrice,
        marketValue,
        gainLoss,
        gainLossPercent,
        // Track whether we're using real-time data or fallback
        usingRealTimePrice: Boolean(
          price && Number.isFinite(price.price.amount)
        ),
      }
    })
  }, [holdings, priceMap])

  if (isLoading || pricesLoading) {
    return (
      <Card>
        <CardContent className="space-y-3 pt-6">
          {[1, 2, 3].map((i) => (
            <Skeleton key={i} className="h-12" />
          ))}
        </CardContent>
      </Card>
    )
  }

  if (holdingsWithRealPrices.length === 0) {
    return (
      <Card>
        <CardContent className="pt-6">
          <p className="text-center text-foreground-secondary">
            No holdings in this portfolio yet
          </p>
        </CardContent>
      </Card>
    )
  }

  return (
    <Card>
      <CardContent className="p-0">
        <div className="overflow-x-auto -mx-4 sm:mx-0">
          <div className="inline-block min-w-full align-middle">
            <table data-testid="holdings-table" className="min-w-full">
              <thead className="border-b border-gray-200 dark:border-gray-700">
                <tr>
                  <th
                    scope="col"
                    className="px-3 sm:px-6 py-3 text-left text-xs font-medium uppercase tracking-wider text-foreground-secondary"
                  >
                    Symbol
                  </th>
                  <th
                    scope="col"
                    className="px-3 sm:px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-foreground-secondary"
                  >
                    Shares
                  </th>
                  <th
                    scope="col"
                    className="hidden sm:table-cell px-3 sm:px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-foreground-secondary"
                  >
                    Avg Cost
                  </th>
                  <th
                    scope="col"
                    className="px-3 sm:px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-foreground-secondary"
                  >
                    Current Price
                  </th>
                  <th
                    scope="col"
                    className="px-3 sm:px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-foreground-secondary"
                  >
                    Market Value
                  </th>
                  <th
                    scope="col"
                    className="hidden md:table-cell px-3 sm:px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-foreground-secondary"
                  >
                    Gain/Loss
                  </th>
                  {onQuickSell && (
                    <th
                      scope="col"
                      className="px-3 sm:px-6 py-3 text-right text-xs font-medium uppercase tracking-wider text-foreground-secondary"
                    >
                      Actions
                    </th>
                  )}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                {holdingsWithRealPrices.map((holding) => {
                  const isPositive = holding.gainLoss >= 0
                  const gainLossColorClass = isPositive
                    ? 'text-positive'
                    : 'text-negative'

                  // Check if we're using real-time price or fallback
                  const usingFallback = !(
                    'usingRealTimePrice' in holding &&
                    holding.usingRealTimePrice
                  )

                  return (
                    <tr
                      key={holding.ticker}
                      data-testid={`holding-row-${holding.ticker}`}
                      className="hover:bg-gray-50 dark:hover:bg-gray-800/50 transition-colors"
                    >
                      <td
                        className="whitespace-nowrap px-3 sm:px-6 py-3 sm:py-4 text-xs sm:text-sm font-medium text-foreground-primary"
                        data-testid={`holding-symbol-${holding.ticker}`}
                      >
                        {holding.ticker}
                      </td>
                      <td
                        className="whitespace-nowrap px-3 sm:px-6 py-3 sm:py-4 text-right text-xs sm:text-sm text-foreground-secondary"
                        data-testid={`holding-quantity-${holding.ticker}`}
                      >
                        {formatNumber(holding.quantity, 0)}
                      </td>
                      <td className="hidden sm:table-cell whitespace-nowrap px-3 sm:px-6 py-3 sm:py-4 text-right text-xs sm:text-sm text-foreground-secondary">
                        {formatCurrency(holding.averageCost)}
                      </td>
                      <td className="whitespace-nowrap px-3 sm:px-6 py-3 sm:py-4 text-right text-xs sm:text-sm text-foreground-secondary">
                        <span className="inline-flex items-center gap-1">
                          {formatCurrency(holding.currentPrice)}
                          {usingFallback && (
                            <span
                              className="text-foreground-tertiary"
                              title="Using average cost (current price unavailable)"
                            >
                              *
                            </span>
                          )}
                        </span>
                      </td>
                      <td
                        className="whitespace-nowrap px-3 sm:px-6 py-3 sm:py-4 text-right text-xs sm:text-sm font-medium text-foreground-primary"
                        data-testid={`holding-value-${holding.ticker}`}
                      >
                        {formatCurrency(holding.marketValue)}
                      </td>
                      <td
                        className={`hidden md:table-cell whitespace-nowrap px-3 sm:px-6 py-3 sm:py-4 text-right text-xs sm:text-sm font-medium ${gainLossColorClass}`}
                      >
                        <div>
                          {isPositive ? '+' : ''}
                          {formatCurrency(holding.gainLoss)}
                        </div>
                        <div className="text-xs">
                          ({formatPercent(holding.gainLossPercent / 100)})
                        </div>
                      </td>
                      {onQuickSell && (
                        <td className="whitespace-nowrap px-3 sm:px-6 py-3 sm:py-4 text-right text-xs sm:text-sm">
                          <Button
                            onClick={() =>
                              onQuickSell(holding.ticker, holding.quantity)
                            }
                            data-testid={`holdings-quick-sell-${holding.ticker.toLowerCase()}`}
                            variant="outline"
                            size="sm"
                            className="text-xs sm:text-sm"
                          >
                            Quick Sell
                          </Button>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}
