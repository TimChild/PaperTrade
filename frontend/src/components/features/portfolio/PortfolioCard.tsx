import { useState } from 'react'
import { Link } from 'react-router-dom'
import type { Portfolio } from '@/types/portfolio'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import { toasts } from '@/utils/toast'
import { useDeletePortfolio } from '@/hooks/usePortfolio'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Skeleton } from '@/components/ui/skeleton'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { cn } from '@/lib/utils'

interface PortfolioCardProps {
  portfolio: Portfolio
  isLoading?: boolean
  onDelete?: (portfolioId: string) => void
}

/**
 * Editorial portfolio card — flush hairline panel with the portfolio name as
 * a small-display heading, a serif tabular total value, and a muted gain/loss
 * delta. Hover bumps the border to amber to telegraph navigation.
 *
 * The card doubles as the link to the portfolio detail; the trash-can delete
 * button sits absolutely positioned in the top-right and stops propagation
 * to avoid triggering the navigation.
 */
export function PortfolioCard({
  portfolio,
  isLoading = false,
  onDelete,
}: PortfolioCardProps): React.JSX.Element {
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const deleteMutation = useDeletePortfolio()

  if (isLoading) {
    return (
      <div
        className="rounded-editorial border border-hairline bg-canvas-raised/40 p-6"
        data-testid="portfolio-card-skeleton"
      >
        <Skeleton className="h-3 w-20 mb-3" />
        <Skeleton className="h-6 w-40 mb-6" />
        <Skeleton className="h-3 w-16 mb-2" />
        <Skeleton className="h-9 w-32 mb-4" />
        <Skeleton className="h-4 w-24" />
      </div>
    )
  }

  const handleDeleteClick = (e: React.MouseEvent): void => {
    e.preventDefault()
    e.stopPropagation()
    setShowDeleteConfirm(true)
  }

  const handleDeleteConfirm = async (): Promise<void> => {
    try {
      await deleteMutation.mutateAsync(portfolio.id)
      toasts.portfolioDeleted()
      onDelete?.(portfolio.id)
      setShowDeleteConfirm(false)
    } catch (error) {
      toasts.portfolioDeleteError()
      console.error('Delete portfolio error:', error)
    }
  }

  const isPositiveChange = portfolio.dailyChange >= 0
  const sign = isPositiveChange ? '+' : ''
  const deltaTone = isPositiveChange ? 'text-gain' : 'text-loss'

  return (
    <>
      <div className="relative">
        <Link
          to={`/portfolio/${portfolio.id}`}
          className="block focus:outline-none"
        >
          <article
            className="group rounded-editorial border border-hairline bg-canvas-raised/40 p-6 transition-colors duration-quick ease-editorial hover:border-amber/60 hover:bg-canvas-raised/60"
            data-testid={`portfolio-card-${portfolio.id}`}
          >
            <Eyebrow>Portfolio</Eyebrow>
            <h2 className="mt-2 mb-6 font-display text-display-sm tracking-tight text-ink pr-8 line-clamp-2">
              {portfolio.name}
            </h2>

            {/* Total value — primary number */}
            <div className="mb-5">
              <Eyebrow>Total value</Eyebrow>
              <p
                className="mt-1.5 font-display tabular-nums text-display-sm text-ink"
                data-testid={`portfolio-card-value-${portfolio.id}`}
              >
                {formatCurrency(portfolio.totalValue)}
              </p>
            </div>

            {/* Day change + cash row */}
            <dl className="grid grid-cols-2 gap-4 pt-4 border-t border-hairline">
              <div>
                <dt className="font-eyebrow text-ink-muted">Day</dt>
                <dd
                  className={cn(
                    'mt-1 font-tabular text-body-sm flex flex-wrap items-baseline gap-x-1.5',
                    deltaTone
                  )}
                  data-testid={`portfolio-card-day-change-${portfolio.id}`}
                >
                  <span>
                    {sign}
                    {formatCurrency(portfolio.dailyChange)}
                  </span>
                  <span className="text-ink-muted">
                    {formatPercent(portfolio.dailyChangePercent)}
                  </span>
                </dd>
              </div>
              <div>
                <dt className="font-eyebrow text-ink-muted">Cash</dt>
                <dd className="mt-1 font-tabular text-body-sm text-ink">
                  {formatCurrency(portfolio.cashBalance)}
                </dd>
              </div>
            </dl>
          </article>
        </Link>

        {/* Delete button — positioned absolutely, stays out of the link's tap target. */}
        <button
          onClick={handleDeleteClick}
          className="absolute right-3 top-3 rounded-editorial p-2 text-ink-faint transition-colors duration-quick ease-editorial hover:bg-loss-soft hover:text-loss"
          aria-label={`Delete ${portfolio.name}`}
          data-testid={`delete-portfolio-${portfolio.id}`}
          style={{ minHeight: 'auto' }}
        >
          <svg
            xmlns="http://www.w3.org/2000/svg"
            className="h-4 w-4"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            aria-hidden="true"
          >
            <path d="M3 6h18" />
            <path d="M19 6v14c0 1-1 2-2 2H7c-1 0-2-1-2-2V6" />
            <path d="M8 6V4c0-1 1-2 2-2h4c1 0 2 1 2 2v2" />
            <line x1="10" y1="11" x2="10" y2="17" />
            <line x1="14" y1="11" x2="14" y2="17" />
          </svg>
        </button>
      </div>

      <ConfirmDialog
        isOpen={showDeleteConfirm}
        title="Delete portfolio?"
        message={`This permanently deletes "${portfolio.name}", including all transactions and holdings. This action cannot be undone.`}
        confirmLabel="Delete portfolio"
        onConfirm={handleDeleteConfirm}
        onCancel={() => setShowDeleteConfirm(false)}
        variant="danger"
        isLoading={deleteMutation.isPending}
      />
    </>
  )
}
