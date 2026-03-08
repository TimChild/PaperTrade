/**
 * Backtests page — list, run and compare backtests
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { RunBacktestForm } from '@/components/features/backtests/RunBacktestForm'
import { useBacktests, useDeleteBacktest } from '@/hooks/useBacktests'
import { useStrategies } from '@/hooks/useStrategies'
import { formatCurrency, formatPercent, formatDate } from '@/utils/formatters'
import type { BacktestRunResponse, BacktestStatus } from '@/services/api/types'
import toast from 'react-hot-toast'

const STATUS_STYLES: Record<BacktestStatus, string> = {
  COMPLETED:
    'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-300',
  PENDING:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  RUNNING:
    'bg-yellow-100 text-yellow-800 dark:bg-yellow-900/30 dark:text-yellow-300',
  FAILED: 'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-300',
}

export function Backtests(): React.JSX.Element {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set())
  const [deleteTarget, setDeleteTarget] = useState<BacktestRunResponse | null>(
    null
  )

  const { data: backtests, isLoading, error } = useBacktests()
  const { data: strategies } = useStrategies()
  const deleteBacktest = useDeleteBacktest()

  const strategyNames: Record<string, string> = {}
  strategies?.forEach((s) => {
    strategyNames[s.id] = s.name
  })

  const toggleSelected = (id: string, completed: boolean) => {
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

  const handleCompare = () => {
    const ids = Array.from(selectedIds).join(',')
    void navigate(`/compare?ids=${ids}`)
  }

  const handleDelete = () => {
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
    <div
      className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8"
      data-testid="backtests-page"
    >
      {/* Page header */}
      <div className="mb-6 flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
            Backtests
          </h2>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Run and compare strategy backtests
          </p>
        </div>
        <div className="flex gap-2">
          {selectedIds.size >= 2 && (
            <Button
              data-testid="compare-selected-button"
              variant="secondary"
              onClick={handleCompare}
            >
              Compare Selected ({selectedIds.size})
            </Button>
          )}
          {!showForm && (
            <Button
              data-testid="run-backtest-button"
              onClick={() => setShowForm(true)}
            >
              Run Backtest
            </Button>
          )}
        </div>
      </div>

      {/* Run backtest form */}
      {showForm && (
        <div className="mb-8" data-testid="run-backtest-section">
          <RunBacktestForm
            onSuccess={() => setShowForm(false)}
            onCancel={() => setShowForm(false)}
          />
        </div>
      )}

      {/* Loading */}
      {isLoading && (
        <div data-testid="backtests-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {/* Error */}
      {error && !isLoading && (
        <div
          data-testid="backtests-error"
          className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20"
        >
          <p className="text-red-600 dark:text-red-400">
            Failed to load backtests. Please try again.
          </p>
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !error && backtests?.length === 0 && (
        <EmptyState
          data-testid="backtests-empty"
          message="No backtests yet. Run one to evaluate your strategies."
          action={
            !showForm ? (
              <Button onClick={() => setShowForm(true)}>
                Run Your First Backtest
              </Button>
            ) : undefined
          }
        />
      )}

      {/* Backtests table */}
      {!isLoading && !error && backtests && backtests.length > 0 && (
        <div
          className="overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"
          data-testid="backtests-table"
        >
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
                <th className="px-4 py-3 text-left">
                  <span className="sr-only">Select</span>
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Name
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Strategy
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Status
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">
                  Total Return
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Date Range
                </th>
                <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
                  Initial Cash
                </th>
                <th className="px-4 py-3 text-right font-medium text-gray-600 dark:text-gray-300">
                  Actions
                </th>
              </tr>
            </thead>
            <tbody>
              {backtests.map((bt) => {
                const isCompleted = bt.status === 'COMPLETED'
                const isSelected = selectedIds.has(bt.id)
                const returnPct =
                  bt.total_return_pct !== null
                    ? parseFloat(bt.total_return_pct) / 100
                    : null

                return (
                  <tr
                    key={bt.id}
                    data-testid={`backtest-row-${bt.id}`}
                    onClick={() => void navigate(`/backtests/${bt.id}`)}
                    className="cursor-pointer border-b border-gray-100 transition-colors hover:bg-gray-50 dark:border-gray-800 dark:hover:bg-gray-800/50"
                  >
                    {/* Checkbox */}
                    <td
                      className="px-4 py-3"
                      onClick={(e) => e.stopPropagation()}
                    >
                      {isCompleted && (
                        <input
                          type="checkbox"
                          data-testid={`backtest-checkbox-${bt.id}`}
                          checked={isSelected}
                          onChange={() => toggleSelected(bt.id, isCompleted)}
                          className="h-4 w-4 rounded border-gray-300 text-blue-600"
                          aria-label={`Select ${bt.backtest_name}`}
                        />
                      )}
                    </td>

                    {/* Name */}
                    <td className="px-4 py-3 font-medium text-gray-900 dark:text-white">
                      {bt.backtest_name}
                    </td>

                    {/* Strategy */}
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                      {bt.strategy_id !== null
                        ? (strategyNames[bt.strategy_id] ?? '—')
                        : '—'}
                    </td>

                    {/* Status badge */}
                    <td className="px-4 py-3">
                      <span
                        className={`rounded-full px-2 py-1 text-xs font-medium ${STATUS_STYLES[bt.status]}`}
                        data-testid={`backtest-status-${bt.id}`}
                      >
                        {bt.status}
                      </span>
                    </td>

                    {/* Total Return */}
                    <td
                      className={`px-4 py-3 text-right ${returnPct !== null ? (returnPct >= 0 ? 'text-green-600 dark:text-green-400' : 'text-red-600 dark:text-red-400') : 'text-gray-400'}`}
                    >
                      {returnPct !== null ? formatPercent(returnPct) : '---'}
                    </td>

                    {/* Date range */}
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                      {formatDate(bt.start_date, false)} –{' '}
                      {formatDate(bt.end_date, false)}
                    </td>

                    {/* Initial cash */}
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-400">
                      {formatCurrency(parseFloat(bt.initial_cash))}
                    </td>

                    {/* Actions */}
                    <td
                      className="px-4 py-3 text-right"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <Button
                        variant="destructive"
                        size="sm"
                        data-testid={`backtest-delete-${bt.id}`}
                        onClick={() => setDeleteTarget(bt)}
                      >
                        Delete
                      </Button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* Delete confirmation */}
      <ConfirmDialog
        isOpen={deleteTarget !== null}
        title="Delete Backtest"
        message={`Are you sure you want to delete "${deleteTarget?.backtest_name ?? ''}"? This action cannot be undone.`}
        confirmLabel="Delete"
        variant="danger"
        onConfirm={handleDelete}
        onCancel={() => setDeleteTarget(null)}
        isLoading={deleteBacktest.isPending}
      />
    </div>
  )
}
