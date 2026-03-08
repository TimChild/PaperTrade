/**
 * Strategy card component displaying strategy info with delete button
 */
import { useState } from 'react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { useDeleteStrategy } from '@/hooks/useStrategies'
import { formatDate } from '@/utils/formatters'
import type { StrategyResponse, StrategyType } from '@/services/api/types'
import toast from 'react-hot-toast'

const STRATEGY_TYPE_LABELS: Record<StrategyType, string> = {
  BUY_AND_HOLD: 'Buy & Hold',
  DOLLAR_COST_AVERAGING: 'Dollar Cost Averaging',
  MOVING_AVERAGE_CROSSOVER: 'Moving Average Crossover',
}

const STRATEGY_TYPE_COLORS: Record<StrategyType, string> = {
  BUY_AND_HOLD: 'bg-blue-100 text-blue-800 dark:bg-blue-900 dark:text-blue-200',
  DOLLAR_COST_AVERAGING:
    'bg-green-100 text-green-800 dark:bg-green-900 dark:text-green-200',
  MOVING_AVERAGE_CROSSOVER:
    'bg-purple-100 text-purple-800 dark:bg-purple-900 dark:text-purple-200',
}

interface StrategyCardProps {
  strategy: StrategyResponse
}

export function StrategyCard({
  strategy,
}: StrategyCardProps): React.JSX.Element {
  const [showConfirm, setShowConfirm] = useState(false)
  const deleteStrategy = useDeleteStrategy()

  const handleDelete = () => {
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
      <Card
        data-testid={`strategy-card-${strategy.id}`}
        className="flex flex-col"
      >
        <CardHeader className="pb-2">
          <div className="flex items-start justify-between gap-2">
            <CardTitle className="text-lg">{strategy.name}</CardTitle>
            <span
              className={`shrink-0 rounded-full px-2 py-1 text-xs font-medium ${STRATEGY_TYPE_COLORS[strategy.strategy_type]}`}
              data-testid="strategy-type-badge"
            >
              {STRATEGY_TYPE_LABELS[strategy.strategy_type]}
            </span>
          </div>
        </CardHeader>
        <CardContent className="flex flex-1 flex-col justify-between gap-4">
          <div>
            <p className="text-sm text-gray-500 dark:text-gray-400">Tickers</p>
            <div className="mt-1 flex flex-wrap gap-1">
              {strategy.tickers.map((ticker) => (
                <span
                  key={ticker}
                  className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs dark:bg-gray-700 dark:text-gray-200"
                >
                  {ticker}
                </span>
              ))}
            </div>
          </div>
          <div className="flex items-center justify-between">
            <p className="text-xs text-gray-400 dark:text-gray-500">
              Created {formatDate(strategy.created_at, false)}
            </p>
            <Button
              variant="destructive"
              size="sm"
              data-testid="strategy-delete-button"
              onClick={() => setShowConfirm(true)}
            >
              Delete
            </Button>
          </div>
        </CardContent>
      </Card>

      <ConfirmDialog
        isOpen={showConfirm}
        title="Delete Strategy"
        message={`Are you sure you want to delete "${strategy.name}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setShowConfirm(false)}
        isLoading={deleteStrategy.isPending}
      />
    </>
  )
}
