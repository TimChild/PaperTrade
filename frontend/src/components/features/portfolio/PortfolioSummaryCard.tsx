import type { Portfolio } from '@/types/portfolio'
import { formatCurrency, formatPercent } from '@/utils/formatters'

interface PortfolioSummaryCardProps {
  portfolio: Portfolio
  isLoading?: boolean
}

export function PortfolioSummaryCard({
  portfolio,
  isLoading = false,
}: PortfolioSummaryCardProps): React.JSX.Element {
  if (isLoading) {
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
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Total Value
          </p>
          <p className="text-3xl font-bold text-gray-900 dark:text-white">
            {formatCurrency(portfolio.totalValue)}
          </p>
        </div>

        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Daily Change
          </p>
          <div className="flex items-baseline gap-2">
            <p className={`text-xl font-semibold ${changeColorClass}`}>
              {isPositiveChange ? '+' : ''}
              {formatCurrency(portfolio.dailyChange)}
            </p>
            <p className={`text-lg font-medium ${changeColorClass}`}>
              ({formatPercent(portfolio.dailyChangePercent)})
            </p>
          </div>
        </div>

        <div className="border-t border-gray-200 pt-4 dark:border-gray-700">
          <div className="flex justify-between">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              Cash Balance
            </p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {formatCurrency(portfolio.cashBalance)}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}
