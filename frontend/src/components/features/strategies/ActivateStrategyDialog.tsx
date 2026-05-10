/**
 * ActivateStrategyDialog — modal letting the user select a paper-trading
 * portfolio and activate a strategy for live execution.
 *
 * Renders inside the existing app shell as a fixed overlay (matching the
 * pattern used by `ConfirmDialog`). The wider `Dialog` component uses the
 * native <dialog> element with showModal(), but we deliberately stick to the
 * fixed-overlay pattern here so JSDOM-based tests don't need the modal
 * polyfill.
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useActivateStrategy } from '@/hooks/useStrategyActivation'
import { usePortfolios } from '@/hooks/usePortfolio'
import type { PortfolioDTO, StrategyResponse } from '@/services/api/types'
import toast from 'react-hot-toast'

interface ActivateStrategyDialogProps {
  isOpen: boolean
  strategy: StrategyResponse
  onClose: () => void
  onSuccess?: () => void
}

/**
 * Filter helper: only PAPER_TRADING portfolios are eligible targets for live
 * strategy activation. The backend's default `GET /portfolios` already
 * excludes BACKTEST portfolios, but we apply the same filter client-side
 * defensively (in case `portfolio_type` is present and BACKTEST somehow
 * leaks through).
 */
function isPaperTradingPortfolio(p: PortfolioDTO): boolean {
  return p.portfolio_type === undefined || p.portfolio_type === 'PAPER_TRADING'
}

export function ActivateStrategyDialog({
  isOpen,
  strategy,
  onClose,
  onSuccess,
}: ActivateStrategyDialogProps): React.JSX.Element | null {
  const [portfolioId, setPortfolioId] = useState('')
  const [error, setError] = useState<string | null>(null)

  const { data: portfoliosPage, isLoading: portfoliosLoading } = usePortfolios()
  const portfolios = (portfoliosPage?.items ?? []).filter(
    isPaperTradingPortfolio
  )
  const activate = useActivateStrategy()

  if (!isOpen) return null

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault()
    if (!portfolioId) {
      setError('Please select a portfolio')
      return
    }
    setError(null)
    activate.mutate(
      {
        strategyId: strategy.id,
        body: { portfolio_id: portfolioId },
      },
      {
        onSuccess: () => {
          toast.success('Strategy activated')
          setPortfolioId('')
          onSuccess?.()
          onClose()
        },
        onError: () => {
          toast.error('Failed to activate strategy')
        },
      }
    )
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50"
      data-testid="activate-strategy-dialog-backdrop"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose()
      }}
    >
      <div
        className="mx-4 w-full max-w-md rounded-lg bg-white p-6 shadow-xl dark:bg-gray-800"
        data-testid="activate-strategy-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby="activate-strategy-dialog-title"
      >
        <h3
          id="activate-strategy-dialog-title"
          className="text-lg font-semibold text-gray-900 dark:text-white"
        >
          Activate Strategy
        </h3>
        <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
          Choose a paper-trading portfolio for &ldquo;{strategy.name}&rdquo; to
          trade into. The strategy runs daily after market close.
        </p>

        <form
          onSubmit={handleSubmit}
          data-testid="activate-strategy-form"
          className="mt-4 space-y-4"
        >
          <div className="space-y-1">
            <Label htmlFor="activate-portfolio-select">Target Portfolio</Label>
            {portfoliosLoading ? (
              <LoadingSpinner size="sm" />
            ) : portfolios.length === 0 ? (
              <p
                className="text-sm text-gray-500 dark:text-gray-400"
                data-testid="activate-strategy-no-portfolios"
              >
                You don&apos;t have any paper-trading portfolios yet. Create one
                first.
              </p>
            ) : (
              <select
                id="activate-portfolio-select"
                data-testid="activate-portfolio-select"
                value={portfolioId}
                onChange={(e) => {
                  setPortfolioId(e.target.value)
                  setError(null)
                }}
                className="flex h-10 w-full rounded-input border border-gray-300 bg-white px-3 py-2 text-sm text-foreground-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-900"
              >
                <option value="">Select a portfolio...</option>
                {portfolios.map((p) => (
                  <option key={p.id} value={p.id}>
                    {p.name}
                  </option>
                ))}
              </select>
            )}
            {error && (
              <p
                className="text-sm text-red-600 dark:text-red-400"
                data-testid="activate-strategy-error"
              >
                {error}
              </p>
            )}
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onClose}
              data-testid="activate-strategy-cancel"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              data-testid="activate-strategy-submit"
              disabled={
                activate.isPending ||
                portfoliosLoading ||
                portfolios.length === 0
              }
            >
              {activate.isPending ? 'Activating...' : 'Activate'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
