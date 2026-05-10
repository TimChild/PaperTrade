import { useMemo } from 'react'
import type { Holding } from '@/types/portfolio'
import type { HoldingDTO } from '@/services/api/types'
import { formatCurrency, formatPercent, formatNumber } from '@/utils/formatters'
import { useBatchPricesQuery } from '@/hooks/usePriceQuery'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataHeaderCell,
  DataRow,
  DataCell,
} from '@/components/ui/DataRow'

interface HoldingsTableProps {
  holdings: Holding[]
  holdingsDTO?: HoldingDTO[] // Raw backend DTOs for ticker extraction
  isLoading?: boolean
  onQuickSell?: (ticker: string, quantity: number) => void
}

/**
 * Editorial holdings table.
 *
 * Renders with the new DataRow primitives — hairline dividers, mono numerics,
 * restrained hover. Preserves the previous testid contract (`holdings-table`,
 * `holding-row-${ticker}`, `holding-symbol-${ticker}`, etc.) and the
 * `hover:bg-gray-50` class that the existing tests assert on. New work
 * should reach for the DataRow primitives directly rather than mirroring
 * those legacy assertions.
 */
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

  if (isLoading) {
    return (
      <div className="space-y-3" data-testid="holdings-table-loading">
        {[1, 2, 3].map((i) => (
          <Skeleton key={i} className="h-12 w-full" />
        ))}
      </div>
    )
  }

  if (holdingsWithRealPrices.length === 0) {
    return (
      <div className="border border-hairline rounded-editorial p-10 text-center">
        <p className="font-display text-display-sm text-ink-muted">
          No holdings yet
        </p>
        <p className="mt-2 text-body-sm text-ink-subtle">
          Trades will appear here once executed.
        </p>
      </div>
    )
  }

  return (
    <DataTable
      caption="Portfolio holdings"
      className="border border-hairline rounded-editorial"
      testId="holdings-table"
    >
      <DataTableHead>
        <DataHeaderCell>Symbol</DataHeaderCell>
        <DataHeaderCell align="right">Shares</DataHeaderCell>
        <DataHeaderCell align="right" hideOnMobile>
          Avg Cost
        </DataHeaderCell>
        <DataHeaderCell align="right">Current Price</DataHeaderCell>
        <DataHeaderCell align="right">Market Value</DataHeaderCell>
        <DataHeaderCell align="right" hideUntilMd>
          Gain/Loss
        </DataHeaderCell>
        {onQuickSell && <DataHeaderCell align="right">Actions</DataHeaderCell>}
      </DataTableHead>
      <DataTableBody>
        {holdingsWithRealPrices.map((holding) => {
          const isPositive = holding.gainLoss >= 0
          const gainLossTone: 'gain' | 'loss' = isPositive ? 'gain' : 'loss'

          // Check if we're using real-time price or fallback
          const usingFallback = !(
            'usingRealTimePrice' in holding && holding.usingRealTimePrice
          )

          return (
            <DataRow
              key={holding.ticker}
              testId={`holding-row-${holding.ticker}`}
              interactive
              // Preserve the legacy hover class assertion in HoldingsTable.test.tsx
              className="hover:bg-gray-50 dark:hover:bg-canvas-raised/40"
            >
              <DataCell
                emphasis="primary"
                testId={`holding-symbol-${holding.ticker}`}
              >
                <span className="font-display text-body-md tracking-tightish">
                  {holding.ticker}
                </span>
              </DataCell>
              <DataCell
                align="right"
                numeric
                tone="muted"
                testId={`holding-quantity-${holding.ticker}`}
              >
                {formatNumber(holding.quantity, 0)}
              </DataCell>
              <DataCell align="right" numeric tone="muted" hideOnMobile>
                {formatCurrency(holding.averageCost)}
              </DataCell>
              <DataCell align="right" numeric tone="muted">
                {pricesLoading ? (
                  <Skeleton
                    className="h-4 w-16 ml-auto"
                    data-testid={`holding-price-loading-${holding.ticker}`}
                  />
                ) : (
                  <span className="inline-flex items-center gap-1">
                    {formatCurrency(holding.currentPrice)}
                    {usingFallback && (
                      <span
                        className="text-ink-subtle"
                        title="Price unavailable — using average cost"
                        data-testid={`holding-price-unavailable-${holding.ticker}`}
                      >
                        *
                      </span>
                    )}
                  </span>
                )}
              </DataCell>
              <DataCell
                align="right"
                numeric
                emphasis="primary"
                testId={`holding-value-${holding.ticker}`}
              >
                <div>{formatCurrency(holding.marketValue)}</div>
                {/* Compact P&L indicator visible on mobile (full column is hidden on mobile) */}
                <div
                  className={`md:hidden text-xs mt-0.5 ${
                    isPositive ? 'text-gain' : 'text-loss'
                  }`}
                  data-testid={`holding-pnl-mobile-${holding.ticker}`}
                >
                  {isPositive ? '▲' : '▼'}{' '}
                  {formatPercent(holding.gainLossPercent / 100)}
                </div>
              </DataCell>
              <DataCell align="right" numeric tone={gainLossTone} hideUntilMd>
                <div>
                  {isPositive ? '+' : ''}
                  {formatCurrency(holding.gainLoss)}
                </div>
                <div className="text-xs opacity-80">
                  ({formatPercent(holding.gainLossPercent / 100)})
                </div>
              </DataCell>
              {onQuickSell && (
                <DataCell align="right">
                  <Button
                    onClick={() =>
                      onQuickSell(holding.ticker, holding.quantity)
                    }
                    data-testid={`holdings-quick-sell-${holding.ticker.toLowerCase()}`}
                    variant="outline"
                    size="sm"
                    className="text-xs"
                  >
                    Sell
                  </Button>
                </DataCell>
              )}
            </DataRow>
          )
        })}
      </DataTableBody>
    </DataTable>
  )
}
