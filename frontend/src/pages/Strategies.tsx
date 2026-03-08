/**
 * Strategies page — list and create trading strategies
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { StrategyCard } from '@/components/features/strategies/StrategyCard'
import { CreateStrategyForm } from '@/components/features/strategies/CreateStrategyForm'
import { useStrategies } from '@/hooks/useStrategies'

export function Strategies(): React.JSX.Element {
  const [showForm, setShowForm] = useState(false)
  const { data: strategies, isLoading, error } = useStrategies()

  return (
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      data-testid="strategies-page"
    >
      {/* Page header */}
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Strategies
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Define trading strategies to use in backtests
          </p>
        </div>
        {!showForm && (
          <Button
            data-testid="create-strategy-button"
            onClick={() => setShowForm(true)}
          >
            Create Strategy
          </Button>
        )}
      </div>

      {/* Create strategy form */}
      {showForm && (
        <div className="mb-8" data-testid="create-strategy-section">
          <CreateStrategyForm
            onSuccess={() => setShowForm(false)}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div data-testid="strategies-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div
          data-testid="strategies-error"
          className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20"
        >
          <p className="text-red-600 dark:text-red-400">
            Failed to load strategies. Please try again.
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && strategies?.length === 0 && (
        <EmptyState
          data-testid="strategies-empty"
          message="No strategies yet. Create one to get started with backtesting."
          action={
            !showForm ? (
              <Button onClick={() => setShowForm(true)}>
                Create Your First Strategy
              </Button>
            ) : undefined
          }
        />
      )}

      {/* Strategy grid */}
      {!isLoading && !error && strategies && strategies.length > 0 && (
        <div
          className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
          data-testid="strategies-grid"
        >
          {strategies.map((strategy) => (
            <StrategyCard key={strategy.id} strategy={strategy} />
          ))}
        </div>
      )}
    </div>
  )
}
