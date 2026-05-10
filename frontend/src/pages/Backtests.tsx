/**
 * Backtests page — editorial library of backtest runs.
 *
 * Layout:
 *   - SectionHeader (eyebrow + serif title) + trailing CTAs ("Compare
 *     Selected" appears once 2+ are checked, plus "Run backtest").
 *   - Form drops in below the header when toggled.
 *   - Backtests render in a hairline DataTable. Row click navigates to
 *     the detail page; the checkbox cell + delete cell stop propagation.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { SectionHeader } from '@/components/ui/SectionHeader'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataRow,
  DataCell,
  DataHeaderCell,
} from '@/components/ui/DataRow'
import { BacktestStatusBadge } from '@/components/features/backtests/BacktestMetrics'
import { RunBacktestForm } from '@/components/features/backtests/RunBacktestForm'
import { useBacktests, useDeleteBacktest } from '@/hooks/useBacktests'
import { useStrategies } from '@/hooks/useStrategies'
import { formatCurrency, formatPercent, formatDate } from '@/utils/formatters'
import type { BacktestRunResponse } from '@/services/api/types'
import toast from 'react-hot-toast'

export function Backtests(): React.JSX.Element {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleteTarget, setDeleteTarget] = useState<BacktestRunResponse | null>(
    null
  )

  const { data: backtestsPage, isLoading, error } = useBacktests()
  const backtests = backtestsPage?.items
  const { data: strategiesPage } = useStrategies()
  const strategies = strategiesPage?.items
  const deleteBacktest = useDeleteBacktest()

  const strategyNames: Record<string, string> = {}
  strategies?.forEach((s) => {
    strategyNames[s.id] = s.name
  })

  const toggleSelected = (id: string, completed: boolean): void => {
    if (!completed) return
    setSelectedIds((prev) => {
      const next = new Set(prev)
      if (next.has(id)) {
        next.delete(id)
      } else {
        next.add(id)
      }
      return next
    })
  }

  const handleCompare = (): void => {
    const ids = Array.from(selectedIds).join(',')
    void navigate(`/compare?ids=${ids}`)
  }

  const handleDelete = (): void => {
    if (!deleteTarget) return
    deleteBacktest.mutate(deleteTarget.id, {
      onSuccess: () => {
        toast.success('Backtest deleted')
        setDeleteTarget(null)
        setSelectedIds((prev) => {
          const next = new Set(prev)
          next.delete(deleteTarget.id)
          return next
        })
      },
      onError: () => {
        toast.error('Failed to delete backtest')
      },
    })
  }

  return (
    <PageFrame>
      <div
        className="reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="backtests-page"
      >
        <SectionHeader
          eyebrow="Research"
          title="Backtests"
          as="h1"
          description="Evaluate strategies against historical market data, then compare runs side-by-side."
          trailing={
            <div className="flex flex-wrap gap-2">
              {selectedIds.size >= 2 && (
                <Button
                  data-testid="compare-selected-button"
                  variant="secondary"
                  onClick={handleCompare}
                >
                  Compare selected ({selectedIds.size})
                </Button>
              )}
              {!showForm && (
                <Button
                  data-testid="run-backtest-button"
                  onClick={() => setShowForm(true)}
                >
                  Run backtest
                </Button>
              )}
            </div>
          }
          withRule
        />
      </div>

      {showForm && (
        <div
          className="mt-8 sm:mt-10 reveal"
          style={{ ['--reveal-delay' as string]: '60ms' }}
          data-testid="run-backtest-section"
        >
          <RunBacktestForm
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
          <div data-testid="backtests-loading" className="py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {error && !isLoading && (
          <div
            data-testid="backtests-error"
            className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
          >
            <p className="text-body-md text-ink">
              Failed to load backtests. Please try again.
            </p>
          </div>
        )}

        {!isLoading && !error && backtests?.length === 0 && (
          <EmptyState
            data-testid="backtests-empty"
            eyebrow="No backtests yet"
            title="Run your first backtest"
            description="A backtest replays a strategy over historical data so you can evaluate its return, drawdown, and trade behaviour before committing real capital."
            action={
              !showForm ? (
                <Button onClick={() => setShowForm(true)}>
                  Run your first backtest
                </Button>
              ) : undefined
            }
          />
        )}

        {!isLoading && !error && backtests && backtests.length > 0 && (
          <DataTable testId="backtests-table">
            <DataTableHead>
              <DataHeaderCell>
                <span className="sr-only">Select</span>
              </DataHeaderCell>
              <DataHeaderCell>Name</DataHeaderCell>
              <DataHeaderCell hideOnMobile>Strategy</DataHeaderCell>
              <DataHeaderCell>Status</DataHeaderCell>
              <DataHeaderCell align="right">Total return</DataHeaderCell>
              <DataHeaderCell hideUntilMd>Date range</DataHeaderCell>
              <DataHeaderCell align="right" hideUntilMd>
                Initial cash
              </DataHeaderCell>
              <DataHeaderCell align="right">
                <span className="sr-only">Actions</span>
              </DataHeaderCell>
            </DataTableHead>
            <DataTableBody>
              {backtests.map((bt) => {
                const isCompleted = bt.status === 'COMPLETED'
                const isSelected = selectedIds.has(bt.id)
                const returnPct =
                  bt.total_return_pct !== null
                    ? parseFloat(bt.total_return_pct) / 100
                    : null
                const returnTone =
                  returnPct !== null
                    ? returnPct >= 0
                      ? 'gain'
                      : 'loss'
                    : 'muted'

                return (
                  <DataRow
                    key={bt.id}
                    testId={`backtest-row-${bt.id}`}
                    onClick={() => void navigate(`/backtests/${bt.id}`)}
                  >
                    {/* Checkbox cell — stops propagation to keep the
                        checkbox toggle separate from row navigation. */}
                    <DataCell
                      onClick={(e) => e.stopPropagation()}
                      className="w-12"
                    >
                      {isCompleted && (
                        <input
                          type="checkbox"
                          data-testid={`backtest-checkbox-${bt.id}`}
                          checked={isSelected}
                          onChange={() => toggleSelected(bt.id, isCompleted)}
                          className="h-4 w-4 rounded-editorial border border-hairline-strong bg-canvas-raised accent-amber"
                          aria-label={`Select ${bt.backtest_name}`}
                        />
                      )}
                    </DataCell>

                    <DataCell emphasis="primary">{bt.backtest_name}</DataCell>

                    <DataCell tone="muted" hideOnMobile>
                      {bt.strategy_id !== null
                        ? (strategyNames[bt.strategy_id] ?? '—')
                        : '—'}
                    </DataCell>

                    <DataCell>
                      <BacktestStatusBadge status={bt.status} />
                    </DataCell>

                    <DataCell align="right" numeric tone={returnTone}>
                      {returnPct !== null ? formatPercent(returnPct) : '---'}
                    </DataCell>

                    <DataCell tone="muted" numeric hideUntilMd>
                      {formatDate(bt.start_date, false)} –{' '}
                      {formatDate(bt.end_date, false)}
                    </DataCell>

                    <DataCell align="right" tone="muted" numeric hideUntilMd>
                      {formatCurrency(parseFloat(bt.initial_cash))}
                    </DataCell>

                    {/* Actions cell — stops propagation to keep delete
                        from also navigating. */}
                    <DataCell
                      align="right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button
                        variant="ghost"
                        size="sm"
                        data-testid={`backtest-delete-${bt.id}`}
                        onClick={() => setDeleteTarget(bt)}
                        className="text-ink-muted hover:text-loss"
                      >
                        Delete
                      </Button>
                    </DataCell>
                  </DataRow>
                )
              })}
            </DataTableBody>
          </DataTable>
        )}
      </section>

      <ConfirmDialog
        isOpen={deleteTarget !== null}
        title="Delete backtest?"
        message={`This permanently removes "${deleteTarget?.backtest_name ?? ''}". This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        isLoading={deleteBacktest.isPending}
      />
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
