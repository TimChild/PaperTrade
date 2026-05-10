/**
 * Strategy card — editorial flush panel pairing the strategy name (display
 * serif) with a small-caps type tag, ticker chips, the live activation
 * surface, and a creation timestamp + delete control.
 */
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { StrategyActivationPanel } from './StrategyActivationPanel'
import { StrategyProvenanceChip } from './StrategyProvenanceChip'
import { useDeleteStrategy } from '@/hooks/useStrategies'
import { formatDate } from '@/utils/formatters'
import type { StrategyResponse, StrategyType } from '@/services/api/types'
import toast from 'react-hot-toast'

const STRATEGY_TYPE_LABELS: Record<StrategyType, string> = {
  BUY_AND_HOLD: 'Buy & Hold',
  DOLLAR_COST_AVERAGING: 'Dollar Cost Averaging',
  MOVING_AVERAGE_CROSSOVER: 'Moving Average Crossover',
}

interface StrategyCardProps {
  strategy: StrategyResponse
}

export function StrategyCard({
  strategy,
}: StrategyCardProps): React.JSX.Element {
  const [showConfirm, setShowConfirm] = useState(false)
  const deleteStrategy = useDeleteStrategy()

  const handleDelete = (): void => {
    deleteStrategy.mutate(strategy.id, {
      onSuccess: () => {
        toast.success('Strategy deleted')
        setShowConfirm(false)
      },
      onError: () => {
        toast.error('Failed to delete strategy')
      },
    })
  }

  return (
    <>
      <article
        data-testid={`strategy-card-${strategy.id}`}
        className="flex flex-col gap-5 rounded-editorial border border-hairline bg-canvas-raised/40 p-6"
      >
        <header className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <Eyebrow>Strategy</Eyebrow>
            <h3 className="mt-1.5 font-display text-display-sm tracking-tight text-ink line-clamp-2">
              <Link
                to={`/strategies/${strategy.id}`}
                className="hover:text-amber transition-colors duration-quick ease-editorial"
                data-testid={`strategy-name-link-${strategy.id}`}
              >
                {strategy.name}
              </Link>
            </h3>
            {/* Provenance chip — agent-authored strategies surface
                "Authored by <label>" beneath the name. Renders null for
                human-authored strategies (the default). */}
            <div className="mt-1">
              <StrategyProvenanceChip strategyId={strategy.id} />
            </div>
          </div>
          <span
            className="shrink-0 inline-flex items-center font-eyebrow rounded-editorial bg-canvas-raised border border-hairline px-2 py-1 text-ink-muted"
            data-testid="strategy-type-badge"
          >
            {STRATEGY_TYPE_LABELS[strategy.strategy_type]}
          </span>
        </header>

        <div>
          <Eyebrow>Tickers</Eyebrow>
          <div className="mt-2 flex flex-wrap gap-1.5">
            {strategy.tickers.map((ticker) => (
              <span
                key={ticker}
                className="rounded-editorial bg-canvas-sunken border border-hairline px-2 py-0.5 font-tabular text-body-sm text-ink"
              >
                {ticker}
              </span>
            ))}
          </div>
        </div>

        {/* Live activation surface — status badge + Activate / Run Now / Deactivate. */}
        <StrategyActivationPanel strategy={strategy} />

        <div className="flex items-center justify-between gap-3 pt-4 border-t border-hairline">
          <p className="font-eyebrow text-ink-subtle">
            Created {formatDate(strategy.created_at, false)}
          </p>
          <Button
            variant="ghost"
            size="sm"
            data-testid="strategy-delete-button"
            onClick={() => setShowConfirm(true)}
            className="text-ink-muted hover:text-loss"
          >
            Delete
          </Button>
        </div>
      </article>

      <ConfirmDialog
        isOpen={showConfirm}
        title="Delete strategy?"
        message={`This permanently removes "${strategy.name}". Any backtests already produced are preserved, but the strategy itself can no longer be edited or activated.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setShowConfirm(false)}
        isLoading={deleteStrategy.isPending}
      />
    </>
  )
}
