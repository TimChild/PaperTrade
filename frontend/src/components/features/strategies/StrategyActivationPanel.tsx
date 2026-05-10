/**
 * StrategyActivationPanel — renders the live-activation surface for a single
 * strategy. Drops into a strategy card or detail view.
 *
 * States:
 *
 * - No activation → "Activate" button
 * - Has activation → status badge + details (target portfolio, last run,
 *   last error if ERROR) + Run Now and Deactivate buttons
 *
 * The panel co-locates the small modal/confirmation flows for run-now and
 * deactivate so the parent only needs to render `<StrategyActivationPanel
 * strategy={...} />` to get the full live-execution UX.
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ActivateStrategyDialog } from './ActivateStrategyDialog'
import { ActivationStatusBadge } from './ActivationStatusBadge'
import {
  useDeactivateActivation,
  useRunActivationNow,
  useStrategyActivation,
} from '@/hooks/useStrategyActivation'
import { usePortfolios } from '@/hooks/usePortfolio'
import { formatDate } from '@/utils/formatters'
import type { StrategyResponse } from '@/services/api/types'
import toast from 'react-hot-toast'

interface StrategyActivationPanelProps {
  strategy: StrategyResponse
}

export function StrategyActivationPanel({
  strategy,
}: StrategyActivationPanelProps): React.JSX.Element {
  const [showActivateDialog, setShowActivateDialog] = useState(false)
  const [showDeactivateConfirm, setShowDeactivateConfirm] = useState(false)
  const [showRunNowConfirm, setShowRunNowConfirm] = useState(false)

  const {
    data: activation,
    isLoading: activationLoading,
    isError: activationError,
  } = useStrategyActivation(strategy.id)

  const { data: portfoliosPage } = usePortfolios()
  const deactivate = useDeactivateActivation()
  const runNow = useRunActivationNow()

  const portfolioName = activation?.portfolio_id
    ? (portfoliosPage?.items.find((p) => p.id === activation.portfolio_id)
        ?.name ?? null)
    : null

  const handleRunNow = (): void => {
    if (!activation) return
    runNow.mutate(
      { activationId: activation.id, strategyId: strategy.id },
      {
        onSuccess: (result) => {
          if (result.succeeded) {
            const tradeWord = result.trades === 1 ? 'trade' : 'trades'
            toast.success(`Run complete: ${result.trades} ${tradeWord}`)
          } else {
            toast.error(`Run failed: ${result.error ?? 'unknown error'}`)
          }
          setShowRunNowConfirm(false)
        },
        onError: () => {
          toast.error('Failed to run activation')
        },
      }
    )
  }

  const handleDeactivate = (): void => {
    if (!activation) return
    deactivate.mutate(
      { activationId: activation.id, strategyId: strategy.id },
      {
        onSuccess: () => {
          toast.success('Activation paused')
          setShowDeactivateConfirm(false)
        },
        onError: () => {
          toast.error('Failed to deactivate')
        },
      }
    )
  }

  if (activationLoading) {
    return (
      <div data-testid={`strategy-activation-loading-${strategy.id}`}>
        <LoadingSpinner size="sm" />
      </div>
    )
  }

  if (activationError) {
    return (
      <div
        data-testid={`strategy-activation-error-${strategy.id}`}
        className="text-xs text-red-600 dark:text-red-400"
      >
        Failed to load activation status
      </div>
    )
  }

  // No activation yet — show Activate button
  if (!activation) {
    return (
      <>
        <div data-testid={`strategy-activation-empty-${strategy.id}`}>
          <Button
            variant="default"
            size="sm"
            data-testid={`strategy-activate-button-${strategy.id}`}
            onClick={() => setShowActivateDialog(true)}
          >
            Activate
          </Button>
        </div>
        <ActivateStrategyDialog
          isOpen={showActivateDialog}
          strategy={strategy}
          onClose={() => setShowActivateDialog(false)}
        />
      </>
    )
  }

  // Has activation — show status + actions
  // ACTIVE/ERROR/PAUSED can all run-now and deactivate; STOPPED is terminal
  // and is not exposed via the deactivate endpoint per backend semantics.
  const canRunNow = activation.status !== 'STOPPED'
  const canDeactivate =
    activation.status === 'ACTIVE' || activation.status === 'ERROR'

  return (
    <>
      <div
        data-testid={`strategy-activation-panel-${strategy.id}`}
        className="space-y-2 rounded-md border border-gray-200 bg-gray-50 p-3 dark:border-gray-700 dark:bg-gray-800/50"
      >
        <div className="flex items-center justify-between gap-2">
          <ActivationStatusBadge status={activation.status} />
          <div className="flex gap-2">
            <Button
              variant="secondary"
              size="sm"
              data-testid={`strategy-run-now-button-${strategy.id}`}
              disabled={!canRunNow || runNow.isPending}
              onClick={() => setShowRunNowConfirm(true)}
            >
              {runNow.isPending ? 'Running...' : 'Run Now'}
            </Button>
            {canDeactivate && (
              <Button
                variant="destructive"
                size="sm"
                data-testid={`strategy-deactivate-button-${strategy.id}`}
                disabled={deactivate.isPending}
                onClick={() => setShowDeactivateConfirm(true)}
              >
                Deactivate
              </Button>
            )}
          </div>
        </div>

        <dl
          className="grid grid-cols-1 gap-x-3 gap-y-1 text-xs sm:grid-cols-2"
          data-testid={`strategy-activation-details-${strategy.id}`}
        >
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Portfolio</dt>
            <dd
              className="font-medium text-gray-900 dark:text-gray-100"
              data-testid={`strategy-activation-portfolio-${strategy.id}`}
            >
              {portfolioName ?? activation.portfolio_id.slice(0, 8)}
            </dd>
          </div>
          <div>
            <dt className="text-gray-500 dark:text-gray-400">Last Run</dt>
            <dd
              className="font-medium text-gray-900 dark:text-gray-100"
              data-testid={`strategy-activation-last-run-${strategy.id}`}
            >
              {activation.last_executed_at
                ? formatDate(activation.last_executed_at, true)
                : 'Never'}
            </dd>
          </div>
        </dl>

        {activation.status === 'ERROR' && activation.last_error && (
          <p
            className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-800 dark:border-red-900/50 dark:bg-red-900/20 dark:text-red-300"
            data-testid={`strategy-activation-last-error-${strategy.id}`}
          >
            {activation.last_error}
          </p>
        )}
      </div>

      <ConfirmDialog
        isOpen={showRunNowConfirm}
        title="Run Strategy Now"
        message={`This will execute "${strategy.name}" against the linked portfolio immediately, generating signals from current market prices. Continue?`}
        confirmLabel="Run Now"
        variant="info"
        onConfirm={handleRunNow}
        onCancel={() => setShowRunNowConfirm(false)}
        isLoading={runNow.isPending}
      />

      <ConfirmDialog
        isOpen={showDeactivateConfirm}
        title="Pause Activation"
        message={`Pause live execution of "${strategy.name}"? The scheduler will stop running this strategy. You can re-activate it later.`}
        confirmLabel="Pause"
        variant="warning"
        onConfirm={handleDeactivate}
        onCancel={() => setShowDeactivateConfirm(false)}
        isLoading={deactivate.isPending}
      />
    </>
  )
}
