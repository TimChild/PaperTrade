import { useState } from 'react'
import { Link } from 'react-router-dom'
import toast from 'react-hot-toast'
import type { Portfolio } from '@/types/portfolio'
import { formatCurrency } from '@/utils/formatters'
import { useDeletePortfolio } from '@/hooks/usePortfolio'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

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
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
        </CardHeader>
        <CardContent className="space-y-4">
          <div>
            <Skeleton className="h-4 w-24 mb-2" />
            <Skeleton className="h-10 w-32" />
          </div>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <Skeleton className="h-3 w-20 mb-2" />
              <Skeleton className="h-5 w-16" />
            </div>
            <div>
              <Skeleton className="h-3 w-20 mb-2" />
              <Skeleton className="h-5 w-16" />
            </div>
          </div>
        </CardContent>
      </Card>
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
    ? 'text-positive'
    : 'text-negative'

  return (
    <>
      <div className="relative">
        <Link to={`/portfolio/${portfolio.id}`} className="block">
          <Card
            variant="interactive"
            data-testid={`portfolio-card-${portfolio.id}`}
          >
            <CardHeader>
              <CardTitle>{portfolio.name}</CardTitle>
            </CardHeader>

            <CardContent className="space-y-4">
              {/* Total Value */}
              <div>
                <p className="text-sm text-foreground-tertiary mb-1">
                  Total Value
                </p>
                <p
                  className="text-value-primary text-foreground-primary"
                  data-testid={`portfolio-card-value-${portfolio.id}`}
                >
                  {formatCurrency(portfolio.totalValue)}
                </p>
              </div>

              {/* Cash Balance & Daily Change */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <p className="text-sm text-foreground-tertiary mb-1">
                    Cash Balance
                  </p>
                  <p className="text-value-secondary text-foreground-primary">
                    {formatCurrency(portfolio.cashBalance)}
                  </p>
                </div>
                <div>
                  <p className="text-sm text-foreground-tertiary mb-1">
                    Daily Change
                  </p>
                  <p className={cn('text-value-secondary', changeColorClass)}>
                    {isPositiveChange ? '+' : ''}
                    {formatCurrency(portfolio.dailyChange)}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
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
