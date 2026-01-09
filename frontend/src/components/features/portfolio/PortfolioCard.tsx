import { useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import type { Portfolio } from '@/types/portfolio'
import { formatCurrency } from '@/utils/formatters'
import { useDeletePortfolio } from '@/hooks/usePortfolio'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'

interface PortfolioCardProps {
  portfolio: Portfolio
  isLoading?: boolean
  onDelete?: (portfolioId: string) => void
}

export function PortfolioCard({
  portfolio,
  isLoading = false,
  onDelete,
}: PortfolioCardProps): React.JSX.Element {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const deleteMutation = useDeletePortfolio()

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

  const handleDeleteClick = (e: React.MouseEvent) => {
    e.preventDefault() // Prevent navigation
    e.stopPropagation()
    setShowDeleteConfirm(true)
  }

  const handleDeleteConfirm = async () => {
    try {
      await deleteMutation.mutateAsync(portfolio.id)
      toast.success('Portfolio deleted successfully')
      onDelete?.(portfolio.id)
      setShowDeleteConfirm(false)
    } catch (error) {
      toast.error('Failed to delete portfolio. Please try again.')
      console.error('Delete portfolio error:', error)
    }
  }

  const isPositiveChange = portfolio.dailyChange >= 0
  const changeColorClass = isPositiveChange
    ? 'text-positive dark:text-positive-light'
    : 'text-negative dark:text-negative-light'

  return (
    <>
      <div className="relative">
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

        {/* Delete button - positioned absolutely in top-right corner */}
        <button
          onClick={handleDeleteClick}
          className="absolute right-2 top-2 rounded p-1.5 text-gray-400 transition-colors hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20 dark:hover:text-red-400"
          aria-label={`Delete ${portfolio.name}`}
          data-testid={`delete-portfolio-${portfolio.id}`}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <path d="M3 6h18" />
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
          </svg>
        </button>
      </div>

      {/* Confirmation Dialog */}
      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete Portfolio?"
        message={`Are you sure you want to delete "${portfolio.name}"? This action cannot be undone. All transactions and holdings data will be permanently deleted.`}
        confirmLabel="Delete Portfolio"
        onConfirm={handleDeleteConfirm}
        onCancel={() => setShowDeleteConfirm(false)}
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </>
  )
}
