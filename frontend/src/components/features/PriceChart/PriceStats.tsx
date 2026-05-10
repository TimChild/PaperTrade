/**
 * Price statistics display component
 * Shows current price, absolute change, and percentage change
 *
 * Uses editorial dark theme: tabular mono numerics, muted gain/loss tones,
 * display-serif current price.
 */

interface PriceStatsProps {
  currentPrice: number | undefined
  change: number | undefined
  changePercent: number | undefined
  currency?: string
}

export function PriceStats({
  currentPrice,
  change,
  changePercent,
  currency = 'USD',
}: PriceStatsProps): React.JSX.Element {
  // Check if we have valid data
  const hasValidData =
    currentPrice !== undefined &&
    Number.isFinite(currentPrice) &&
    change !== undefined &&
    Number.isFinite(change) &&
    changePercent !== undefined &&
    Number.isFinite(changePercent)

  if (!hasValidData) {
    return (
      <div className="mb-4">
        <div className="font-display text-display-sm tabular-nums text-ink">
          —
        </div>
        <div className="mt-1 text-body-sm text-ink-subtle">
          Price data unavailable
        </div>
      </div>
    )
  }

  const isPositive = change >= 0
  const colorClass = isPositive ? 'text-gain' : 'text-loss'

  const formatCurrency = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency,
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    }).format(value)
  }

  const formatPercent = (value: number): string => {
    return new Intl.NumberFormat('en-US', {
      style: 'percent',
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
      signDisplay: 'always',
    }).format(value / 100)
  }

  return (
    <div className="mb-4 flex flex-wrap items-baseline gap-x-4 gap-y-1">
      <div className="font-display tabular-nums text-display-sm text-ink">
        {formatCurrency(currentPrice)}
      </div>
      <div className={`font-tabular text-body-md ${colorClass}`}>
        {isPositive ? '+' : ''}
        {formatCurrency(change)}
      </div>
      <div className={`font-tabular text-body-md ${colorClass}`}>
        {formatPercent(changePercent)}
      </div>
    </div>
  )
}
