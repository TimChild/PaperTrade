/**
 * Exploration tasks dashboard (Phase H1) — the human-facing surface for
 * the agent ↔ human task queue.
 *
 * Layout:
 *
 *   - SectionHeader (eyebrow + serif title) with a "New task" amber CTA.
 *   - Inline create form drops in below the header when toggled.
 *   - MetricStat triplet summarises queue health (open / claimed / done).
 *   - Status filter pill row.
 *   - DataTable with hairline rows; row click opens the detail view.
 *
 * The list scope is `mine` so users see their own tasks across every
 * status. The status filter applies on top.
 */
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { MetricStat } from '@/components/ui/MetricStat'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataRow,
  DataCell,
  DataHeaderCell,
} from '@/components/ui/DataRow'
import { ExplorationTaskStatusBadge } from '@/components/features/exploration-tasks/ExplorationTaskStatusBadge'
import { CreateExplorationTaskForm } from '@/components/features/exploration-tasks/CreateExplorationTaskForm'
import { useExplorationTasks } from '@/hooks/useExplorationTasks'
import { usePortfolios } from '@/hooks/usePortfolio'
import { formatDate } from '@/utils/formatters'
import { extractTaskTitle } from '@/utils/explorationTaskTitle'
import type {
  ExplorationTaskResponse,
  ExplorationTaskStatus,
} from '@/services/api/types'
import { cn } from '@/lib/utils'

type StatusFilter = ExplorationTaskStatus | 'ALL'

const FILTERS: { value: StatusFilter; label: string }[] = [
  { value: 'ALL', label: 'All' },
  { value: 'OPEN', label: 'Open' },
  { value: 'IN_PROGRESS', label: 'Claimed' },
  { value: 'DONE', label: 'Done' },
  { value: 'ABANDONED', label: 'Abandoned' },
]

function sortByCreatedAtDesc(
  a: ExplorationTaskResponse,
  b: ExplorationTaskResponse
): number {
  return b.created_at.localeCompare(a.created_at)
}

export function ExplorationTasks(): React.JSX.Element {
  const navigate = useNavigate()
  const [showForm, setShowForm] = useState(false)
  const [statusFilter, setStatusFilter] = useState<StatusFilter>('ALL')

  // Fetch the user's tasks. We pass `scope: 'mine'` so users see their own
  // queue across every status, and apply the status filter on top.
  const {
    data: tasksPage,
    isLoading,
    error,
  } = useExplorationTasks(
    statusFilter === 'ALL'
      ? { scope: 'mine' }
      : { scope: 'mine', status: statusFilter }
  )

  const { data: portfoliosPage } = usePortfolios()
  const portfolioNames: Record<string, string> = {}
  portfoliosPage?.items.forEach((p) => {
    portfolioNames[p.id] = p.name
  })

  const tasks = tasksPage?.items
  const sortedTasks = tasks ? [...tasks].sort(sortByCreatedAtDesc) : undefined

  // Compute the summary counts. Under a status filter, the totals reflect
  // the filtered subset — but the eyebrow stats stay meaningful because the
  // list reflects the same scope. Showing dashes when totals are zero keeps
  // the row from feeling broken on a fresh account.
  const statusCounts = sortedTasks?.reduce(
    (acc, t) => {
      acc[t.status] = (acc[t.status] ?? 0) + 1
      return acc
    },
    {} as Record<ExplorationTaskStatus, number>
  )

  return (
    <PageFrame>
      <div
        className="pt-4 sm:pt-5 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="exploration-tasks-page"
      >
        <SectionHeader
          eyebrow="Agent ↔ human"
          title="Exploration tasks"
          as="h1"
          description="Queue free-form prompts for an agent to investigate. Agents claim tasks from this queue, work the prompt, and submit findings back here."
          trailing={
            !showForm ? (
              <Button
                data-testid="exploration-task-new-btn"
                onClick={() => setShowForm(true)}
              >
                New task
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
          data-testid="exploration-task-create-section"
        >
          <CreateExplorationTaskForm onCancel={() => setShowForm(false)} />
        </div>
      )}

      {/* Stats row — only renders once we have data to summarise. */}
      {sortedTasks && sortedTasks.length > 0 && (
        <section
          className="mt-8 sm:mt-10 reveal grid grid-cols-3 gap-4 sm:gap-8"
          style={{ ['--reveal-delay' as string]: '120ms' }}
          data-testid="exploration-tasks-stats"
        >
          <MetricStat
            label="Open"
            value={statusCounts?.OPEN ?? 0}
            size="md"
            testId="exploration-tasks-stat-open"
          />
          <MetricStat
            label="Claimed"
            value={statusCounts?.IN_PROGRESS ?? 0}
            size="md"
            tone="accent"
            testId="exploration-tasks-stat-claimed"
          />
          <MetricStat
            label="Done"
            value={statusCounts?.DONE ?? 0}
            size="md"
            tone="gain"
            testId="exploration-tasks-stat-done"
          />
        </section>
      )}

      {/* Filter pill row — visible whenever the data has loaded so users can
          pivot between empty/non-empty subsets. */}
      <section
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '180ms' }}
      >
        <div
          className="mb-6 flex flex-wrap gap-2"
          data-testid="exploration-tasks-filter-row"
          role="tablist"
          aria-label="Filter exploration tasks by status"
        >
          {FILTERS.map(({ value, label }) => {
            const isActive = statusFilter === value
            return (
              <button
                key={value}
                type="button"
                role="tab"
                aria-selected={isActive}
                data-testid={`exploration-tasks-filter-${value}`}
                onClick={() => setStatusFilter(value)}
                className={cn(
                  'rounded-editorial border px-3 py-1.5 font-eyebrow transition-colors duration-quick ease-editorial',
                  isActive
                    ? 'border-amber bg-amber-soft text-amber'
                    : 'border-hairline bg-canvas-raised/40 text-ink-muted hover:border-hairline-strong hover:text-ink'
                )}
              >
                {label}
              </button>
            )
          })}
        </div>

        {isLoading && (
          <div data-testid="exploration-tasks-loading" className="py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {error && !isLoading && (
          <div
            data-testid="exploration-tasks-error"
            className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
          >
            <p className="text-body-md text-ink">
              Failed to load exploration tasks. Please try again.
            </p>
          </div>
        )}

        {!isLoading && !error && sortedTasks?.length === 0 && (
          <EmptyState
            data-testid="exploration-tasks-empty"
            eyebrow={
              statusFilter === 'ALL'
                ? 'No tasks yet'
                : `No ${statusFilter.toLowerCase().replace(/_/g, ' ')} tasks`
            }
            title={
              statusFilter === 'ALL'
                ? 'Queue your first exploration task'
                : 'Nothing in this state right now'
            }
            description={
              statusFilter === 'ALL'
                ? 'Agents claim tasks from this queue and report findings back. Start with a free-form prompt — the more concrete, the better.'
                : 'Try a different status filter or queue a new task to populate the queue.'
            }
            action={
              statusFilter === 'ALL' && !showForm ? (
                <Button onClick={() => setShowForm(true)}>
                  Queue your first task
                </Button>
              ) : undefined
            }
          />
        )}

        {!isLoading && !error && sortedTasks && sortedTasks.length > 0 && (
          <DataTable testId="exploration-tasks-table">
            <DataTableHead>
              <DataHeaderCell>Status</DataHeaderCell>
              <DataHeaderCell>Title</DataHeaderCell>
              <DataHeaderCell hideOnMobile>Portfolio</DataHeaderCell>
              <DataHeaderCell hideUntilMd>Tickers</DataHeaderCell>
              <DataHeaderCell hideOnMobile>Claimed by</DataHeaderCell>
              <DataHeaderCell align="right" hideOnMobile>
                Created
              </DataHeaderCell>
            </DataTableHead>
            <DataTableBody>
              {sortedTasks.map((task) => {
                const portfolioName = task.target_portfolio_id
                  ? (portfolioNames[task.target_portfolio_id] ??
                    task.target_portfolio_id.slice(0, 8))
                  : '—'
                const title = extractTaskTitle(task.prompt)
                return (
                  <DataRow
                    key={task.id}
                    testId={`exploration-task-list-row-${task.id}`}
                    interactive
                    className="cursor-pointer"
                    onClick={() =>
                      void navigate(`/exploration-tasks/${task.id}`)
                    }
                  >
                    <DataCell>
                      <ExplorationTaskStatusBadge status={task.status} />
                    </DataCell>
                    <DataCell emphasis="primary">
                      <span className="block truncate max-w-[28rem]">
                        {title}
                      </span>
                    </DataCell>
                    <DataCell tone="muted" hideOnMobile>
                      {task.target_portfolio_id ? (
                        <Link
                          to={`/portfolio/${task.target_portfolio_id}`}
                          onClick={(e) => e.stopPropagation()}
                          className="hover:text-amber underline-offset-4 hover:underline"
                          data-testid={`exploration-task-list-portfolio-link-${task.id}`}
                        >
                          {portfolioName}
                        </Link>
                      ) : (
                        '—'
                      )}
                    </DataCell>
                    <DataCell tone="muted" hideUntilMd>
                      {task.tickers && task.tickers.length > 0 ? (
                        <div className="flex flex-wrap gap-1">
                          {task.tickers.slice(0, 4).map((t) => (
                            <span
                              key={t}
                              className="rounded-editorial bg-canvas-sunken border border-hairline px-1.5 py-0.5 font-tabular text-[0.7rem] text-ink"
                            >
                              {t}
                            </span>
                          ))}
                          {task.tickers.length > 4 && (
                            <span className="font-tabular text-[0.7rem] text-ink-subtle">
                              +{task.tickers.length - 4}
                            </span>
                          )}
                        </div>
                      ) : (
                        '—'
                      )}
                    </DataCell>
                    <DataCell tone="muted" hideOnMobile>
                      <span className="font-tabular">
                        {task.claimed_by ?? '—'}
                      </span>
                    </DataCell>
                    <DataCell align="right" tone="muted" numeric hideOnMobile>
                      {formatDate(task.created_at, true)}
                    </DataCell>
                  </DataRow>
                )
              })}
            </DataTableBody>
          </DataTable>
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
