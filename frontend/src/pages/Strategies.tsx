/**
 * Strategies page — editorial library of trading strategies.
 *
 * Layout:
 *   - SectionHeader (eyebrow + serif title) introduces the page; a hairline
 *     rule separates header from content.
 *   - Trailing slot holds the "Create strategy" CTA when the form isn't
 *     showing.
 *   - The grid renders editorial StrategyCards in a 1/2/3 column layout.
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StrategyCard } from '@/components/features/strategies/StrategyCard'
import { CreateStrategyForm } from '@/components/features/strategies/CreateStrategyForm'
import { useStrategies } from '@/hooks/useStrategies'

export function Strategies(): React.JSX.Element {
  const [showForm, setShowForm] = useState(false)
  const { data: strategiesPage, isLoading, error } = useStrategies()
  const strategies = strategiesPage?.items

  return (
    <PageFrame>
      <div
        className="reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="strategies-page"
      >
        <SectionHeader
          eyebrow="Library"
          title="Strategies"
          as="h1"
          description="Define trading strategies, run backtests, and activate them for live execution against a paper-trading portfolio."
          trailing={
            !showForm ? (
              <Button
                data-testid="create-strategy-button"
                onClick={() => setShowForm(true)}
              >
                Create strategy
              </Button>
            ) : undefined
          }
          withRule
        />
      </div>

      {showForm && (
        <div
          className="mt-8 sm:mt-10 reveal"
          style={{ ['--reveal-delay' as string]: '60ms' }}
          data-testid="create-strategy-section"
        >
          <CreateStrategyForm
            onSuccess={() => setShowForm(false)}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      <section
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        {isLoading && (
          <div data-testid="strategies-loading" className="py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {error && !isLoading && (
          <div
            data-testid="strategies-error"
            className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
          >
            <p className="text-body-md text-ink">
              Failed to load strategies. Please try again.
            </p>
          </div>
        )}

        {!isLoading && !error && strategies?.length === 0 && (
          <EmptyState
            data-testid="strategies-empty"
            eyebrow="No strategies yet"
            title="Define your first strategy"
            description="Strategies describe how trades should be generated — buy & hold, dollar-cost averaging, or moving-average crossover. You'll backtest them next."
            action={
              !showForm ? (
                <Button onClick={() => setShowForm(true)}>
                  Create your first strategy
                </Button>
              ) : undefined
            }
          />
        )}

        {!isLoading && !error && strategies && strategies.length > 0 && (
          <>
            <p
              className="mb-6 font-eyebrow text-ink-muted"
              data-testid="strategies-count-label"
            >
              {strategies.length} strateg{strategies.length === 1 ? 'y' : 'ies'}
            </p>
            <div
              className="grid grid-cols-1 gap-5 sm:gap-6 sm:grid-cols-2 lg:grid-cols-3"
              data-testid="strategies-grid"
            >
              {strategies.map((strategy) => (
                <StrategyCard key={strategy.id} strategy={strategy} />
              ))}
            </div>
          </>
        )}
      </section>
    </PageFrame>
  )
}

function PageFrame({
  children,
}: {
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="min-h-screen bg-canvas">
      <div className="mx-auto max-w-[1240px] px-5 sm:px-8 lg:px-12 py-8 sm:py-12 lg:py-16">
        {children}
      </div>
    </div>
  )
}
