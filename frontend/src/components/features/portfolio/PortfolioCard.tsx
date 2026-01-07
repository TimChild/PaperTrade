import { Link } from 'react-router-dom'
import type { Portfolio } from '@/types/portfolio'
import { formatCurrency } from '@/utils/formatters'

interface PortfolioCardProps {
  portfolio: Portfolio
  isLoading?: boolean
}

export function PortfolioCard({
  portfolio,
  isLoading = false,
}: PortfolioCardProps): React.JSX.Element {
  if (isLoading) {
    return (
      <div className="rounded-lg border border-gray-300 bg-white p-6 dark:border-gray-700 dark:bg-gray-800">
        <div className="animate-pulse space-y-4">
          <div className="h-6 w-48 rounded bg-gray-300 dark:bg-gray-700"></div>
          <div className="h-8 w-32 rounded bg-gray-300 dark:bg-gray-700"></div>
        </div>
      </div>
    )
  }

  const isPositiveChange = portfolio.dailyChange >= 0
  const changeColorClass = isPositiveChange
    ? 'text-positive dark:text-positive-light'
    : 'text-negative dark:text-negative-light'

  return (
    <Link
      to={`/portfolio/${portfolio.id}`}
      data-testid={`portfolio-card-${portfolio.id}`}
      className="block rounded-lg border border-gray-300 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:border-blue-400 dark:border-gray-700 dark:bg-gray-800 dark:hover:border-blue-500"
    >
      <div className="mb-4">
        <h3 className="text-xl font-semibold text-gray-900 dark:text-white">
          {portfolio.name}
        </h3>
      </div>

      <div className="space-y-3">
        <div>
          <p className="text-sm text-gray-600 dark:text-gray-400">
            Total Value
          </p>
          <p
            className="text-2xl font-bold text-gray-900 dark:text-white"
            data-testid={`portfolio-card-value-${portfolio.id}`}
          >
            {formatCurrency(portfolio.totalValue)}
          </p>
        </div>

        <div className="flex items-center justify-between border-t border-gray-200 pt-3 dark:border-gray-700">
          <div>
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Cash Balance
            </p>
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {formatCurrency(portfolio.cashBalance)}
            </p>
          </div>
          <div className="text-right">
            <p className="text-xs text-gray-600 dark:text-gray-400">
              Daily Change
            </p>
            <p className={`text-sm font-medium ${changeColorClass}`}>
              {isPositiveChange ? '+' : ''}
              {formatCurrency(portfolio.dailyChange)}
            </p>
          </div>
        </div>
      </div>
    </Link>
  )
}
