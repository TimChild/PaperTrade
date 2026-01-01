/**
 * Price statistics display component
 * Shows current price, absolute change, and percentage change
 */

interface PriceStatsProps {
  currentPrice: number
  change: number
  changePercent: number
  currency?: string
}

export function PriceStats({
  currentPrice,
  change,
  changePercent,
  currency = 'USD',
}: PriceStatsProps): React.JSX.Element {
  const isPositive = change >= 0
  const colorClass = isPositive
    ? 'text-green-600 dark:text-green-400'
    : 'text-red-600 dark:text-red-400'

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
    <div className="mb-4 flex items-baseline gap-4">
      <div className="text-3xl font-bold text-gray-900 dark:text-white">
        {formatCurrency(currentPrice)}
      </div>
      <div className={`text-lg font-semibold ${colorClass}`}>
        {isPositive ? '+' : ''}
        {formatCurrency(change)}
      </div>
      <div className={`text-lg font-semibold ${colorClass}`}>
        {formatPercent(changePercent)}
      </div>
    </div>
  )
}
