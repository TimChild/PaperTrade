/**
 * Exploration task detail (Phase H1).
 *
 * Layout:
 *
 *   - Back link to the list.
 *   - Eyebrow + serif headline derived from the prompt.
 *   - Status badge inline with the headline metadata.
 *   - Panels for: full prompt, claim history, findings (when DONE),
 *     constraints (when present), and an Abandon CTA for the creator
 *     while the task is OPEN.
 *
 * The prompt + summary render as preformatted text with line breaks
 * preserved (`whitespace-pre-wrap`). A future iteration can swap in a
 * markdown renderer once we add the dependency.
 */
import { Link, useNavigate, useParams } from 'react-router-dom'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { isAxiosError } from 'axios'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { Caption } from '@/components/ui/Caption'
import { Panel } from '@/components/ui/Panel'
import { ExplorationTaskStatusBadge } from '@/components/features/exploration-tasks/ExplorationTaskStatusBadge'
import {
  useAbandonExplorationTask,
  useExplorationTask,
} from '@/hooks/useExplorationTasks'
import { usePortfolios } from '@/hooks/usePortfolio'
import { formatDate } from '@/utils/formatters'
import { extractTaskBody, extractTaskTitle } from '@/utils/explorationTaskTitle'
import type { ExplorationTaskResponse } from '@/services/api/types'

export function ExplorationTaskDetail(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const taskId = id ?? ''
  const navigate = useNavigate()
  const [showAbandonConfirm, setShowAbandonConfirm] = useState(false)

  const { data: task, isLoading, error } = useExplorationTask(taskId)
  const { data: portfoliosPage } = usePortfolios()
  const portfolios = portfoliosPage?.items ?? []
  const abandonTask = useAbandonExplorationTask()

  if (isLoading) {
    return (
      <PageFrame>
        <div data-testid="exploration-task-detail-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      </PageFrame>
    )
  }

  if (error || !task) {
    const isNotFound = isAxiosError(error) && error.response?.status === 404
    return (
      <PageFrame>
        <BackLink />
        <div
          data-testid="exploration-task-detail-error"
          className="mt-6 rounded-editorial border border-hairline bg-loss-soft/40 p-6"
        >
          <Eyebrow tone="accent">{isNotFound ? 'Not found' : 'Error'}</Eyebrow>
          <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
            {isNotFound
              ? 'This exploration task could not be found'
              : 'Failed to load this exploration task'}
          </h2>
          <p className="mt-2 text-body-sm text-ink-muted">
            {isNotFound
              ? 'It may have been abandoned by its creator. Try heading back to the list.'
              : 'Try refreshing the page. If the problem persists the backend may be unreachable.'}
          </p>
        </div>
      </PageFrame>
    )
  }

  const targetPortfolio = task.target_portfolio_id
    ? portfolios.find((p) => p.id === task.target_portfolio_id)
    : null
  const title = extractTaskTitle(task.prompt)
  const body = extractTaskBody(task.prompt)
  const canAbandon = task.status === 'OPEN'

  const handleAbandon = (): void => {
    abandonTask.mutate(task.id, {
      onSuccess: () => {
        toast.success('Exploration task abandoned')
        setShowAbandonConfirm(false)
        void navigate('/exploration-tasks')
      },
      onError: () => {
        toast.error('Failed to abandon task')
      },
    })
  }

  return (
    <PageFrame>
      <BackLink />

      {/* Hero */}
      <header
        className="mt-4 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="exploration-task-detail-page"
      >
        <Eyebrow>Agent ↔ human · Exploration task</Eyebrow>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <h1
            className="font-display text-display-md sm:text-display-lg tracking-tight text-ink max-w-3xl"
            data-testid="exploration-task-detail-title"
          >
            {title}
          </h1>
          <div className="flex flex-shrink-0 items-center gap-3">
            <ExplorationTaskStatusBadge status={task.status} />
            {canAbandon && (
              <Button
                variant="ghost"
                onClick={() => setShowAbandonConfirm(true)}
                data-testid="exploration-task-detail-abandon-btn"
                className="text-ink-muted hover:text-loss"
              >
                Abandon
              </Button>
            )}
          </div>
        </div>
        <Caption className="mt-3 block text-ink-subtle">
          Created {formatDate(task.created_at, true)} · Last updated{' '}
          {formatDate(task.updated_at, true)}
        </Caption>
      </header>

      {/* Prompt body — only rendered when there's content beyond the title.
          The headline already sits in the hero; repeating it as the body
          would feel redundant. */}
      {body.length > 0 && (
        <section
          className="mt-8 reveal"
          style={{ ['--reveal-delay' as string]: '60ms' }}
        >
          <Panel>
            <Eyebrow>Prompt</Eyebrow>
            <p
              className="mt-3 font-sans text-body-md text-ink whitespace-pre-wrap leading-relaxed"
              data-testid="exploration-task-detail-prompt"
            >
              {body}
            </p>
          </Panel>
        </section>
      )}

      {/* Metadata */}
      <section
        className="mt-8 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        <Panel>
          <Eyebrow>Scope</Eyebrow>
          <dl
            className="mt-4 grid gap-5 sm:grid-cols-3"
            data-testid="exploration-task-detail-metadata"
          >
            <MetadataField label="Target portfolio">
              {targetPortfolio ? (
                <Link
                  to={`/portfolio/${targetPortfolio.id}`}
                  className="text-amber underline-offset-4 hover:underline"
                  data-testid="exploration-task-detail-portfolio-link"
                >
                  {targetPortfolio.name}
                </Link>
              ) : task.target_portfolio_id ? (
                <span className="font-tabular text-ink-muted">
                  {task.target_portfolio_id}
                </span>
              ) : (
                <span className="text-ink-subtle">No specific portfolio</span>
              )}
            </MetadataField>
            <MetadataField label="Tickers">
              {task.tickers && task.tickers.length > 0 ? (
                <div
                  className="flex flex-wrap gap-1.5"
                  data-testid="exploration-task-detail-tickers"
                >
                  {task.tickers.map((t) => (
                    <span
                      key={t}
                      className="rounded-editorial bg-canvas-sunken border border-hairline px-2 py-0.5 font-tabular text-body-sm text-ink"
                    >
                      {t}
                    </span>
                  ))}
                </div>
              ) : (
                <span className="text-ink-subtle">Any tickers</span>
              )}
            </MetadataField>
            <MetadataField label="Created by">
              <span className="font-tabular text-body-sm text-ink-muted">
                {task.created_by}
              </span>
            </MetadataField>
          </dl>
        </Panel>
      </section>

      {/* Constraints (only if any are set) */}
      {task.constraints && (
        <section
          className="mt-6 reveal"
          style={{ ['--reveal-delay' as string]: '180ms' }}
        >
          <Panel>
            <Eyebrow>Constraints</Eyebrow>
            <dl
              className="mt-4 grid gap-5 sm:grid-cols-3"
              data-testid="exploration-task-detail-constraints"
            >
              <MetadataField label="Max backtests">
                <span className="font-tabular text-body-md text-ink">
                  {task.constraints.max_backtests ?? 'Unlimited'}
                </span>
              </MetadataField>
              <MetadataField label="Live activation">
                <span className="text-body-md text-ink">
                  {task.constraints.allow_live_activation
                    ? 'Allowed'
                    : 'Research-only'}
                </span>
              </MetadataField>
              <MetadataField label="Strategy whitelist">
                {task.constraints.strategy_type_whitelist &&
                task.constraints.strategy_type_whitelist.length > 0 ? (
                  <div className="flex flex-wrap gap-1.5">
                    {task.constraints.strategy_type_whitelist.map((s) => (
                      <span
                        key={s}
                        className="rounded-editorial bg-canvas-sunken border border-hairline px-2 py-0.5 font-tabular text-body-sm text-ink"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                ) : (
                  <span className="text-ink-subtle">Any strategy type</span>
                )}
              </MetadataField>
            </dl>
          </Panel>
        </section>
      )}

      {/* Claim history */}
      <section
        className="mt-6 reveal"
        style={{ ['--reveal-delay' as string]: '240ms' }}
      >
        <Panel>
          <Eyebrow>Claim</Eyebrow>
          <ClaimSummary task={task} />
        </Panel>
      </section>

      {/* Findings — only when DONE */}
      {task.status === 'DONE' && task.findings && (
        <section
          className="mt-6 reveal"
          style={{ ['--reveal-delay' as string]: '300ms' }}
        >
          <Panel>
            <Eyebrow tone="accent">Findings</Eyebrow>
            <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
              Agent submission
            </h2>
            <p
              className="mt-4 font-sans text-body-md text-ink whitespace-pre-wrap leading-relaxed"
              data-testid="exploration-task-detail-findings-summary"
            >
              {task.findings.summary}
            </p>

            {task.findings.notes && task.findings.notes.length > 0 && (
              <div
                className="mt-5"
                data-testid="exploration-task-detail-findings-notes"
              >
                <Eyebrow>Notes</Eyebrow>
                <ul className="mt-2 list-disc space-y-1 pl-5 text-body-sm text-ink-muted">
                  {task.findings.notes.map((note, i) => (
                    <li key={i}>{note}</li>
                  ))}
                </ul>
              </div>
            )}

            {task.findings.backtest_run_ids.length > 0 && (
              <div
                className="mt-5"
                data-testid="exploration-task-detail-findings-backtests"
              >
                <Eyebrow>Backtests produced</Eyebrow>
                <ul className="mt-2 space-y-1 text-body-sm">
                  {task.findings.backtest_run_ids.map((bid) => (
                    <li key={bid}>
                      <Link
                        to={`/backtests/${bid}`}
                        className="text-amber underline-offset-4 hover:underline font-tabular"
                        data-testid={`exploration-task-detail-backtest-link-${bid}`}
                      >
                        {bid}
                      </Link>
                    </li>
                  ))}
                </ul>
              </div>
            )}

            {task.findings.strategy_ids.length > 0 && (
              <div
                className="mt-5"
                data-testid="exploration-task-detail-findings-strategies"
              >
                <Eyebrow>Strategies authored</Eyebrow>
                <ul className="mt-2 space-y-1 text-body-sm">
                  {task.findings.strategy_ids.map((sid) => (
                    <li
                      key={sid}
                      className="font-tabular text-ink-muted"
                      data-testid={`exploration-task-detail-strategy-id-${sid}`}
                    >
                      {sid}
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>
        </section>
      )}

      <ConfirmDialog
        isOpen={showAbandonConfirm}
        title="Abandon this task?"
        message="Abandoning the task removes it from the queue. Agents will no longer be able to claim it. This cannot be undone."
        confirmLabel="Abandon task"
        variant="danger"
        onConfirm={handleAbandon}
        onCancel={() => setShowAbandonConfirm(false)}
        isLoading={abandonTask.isPending}
      />
    </PageFrame>
  )
}

/**
 * Renders the claim metadata for a task. The shape changes per status —
 * an OPEN task shows a "no agent yet" hint, IN_PROGRESS / DONE / ABANDONED
 * surfaces the agent label and timestamp.
 */
function ClaimSummary({
  task,
}: {
  task: ExplorationTaskResponse
}): React.JSX.Element {
  if (task.status === 'OPEN') {
    return (
      <p
        className="mt-3 text-body-sm text-ink-subtle"
        data-testid="exploration-task-detail-claim-open"
      >
        Not yet claimed by an agent.
      </p>
    )
  }

  return (
    <dl
      className="mt-4 grid gap-5 sm:grid-cols-2"
      data-testid="exploration-task-detail-claim"
    >
      <MetadataField label="Claimed by">
        <span
          className="font-tabular text-body-md text-ink"
          data-testid="exploration-task-detail-claimed-by"
        >
          {task.claimed_by ?? '—'}
        </span>
      </MetadataField>
      <MetadataField label="Claimed at">
        <span className="font-tabular text-body-md text-ink-muted">
          {task.claimed_at ? formatDate(task.claimed_at, true) : '—'}
        </span>
      </MetadataField>
    </dl>
  )
}

function MetadataField({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}): React.JSX.Element {
  return (
    <div className="space-y-1.5">
      <dt>
        <Eyebrow>{label}</Eyebrow>
      </dt>
      <dd>{children}</dd>
    </div>
  )
}

function BackLink(): React.JSX.Element {
  return (
    <Link
      to="/exploration-tasks"
      data-testid="exploration-task-detail-back-link"
      className="font-eyebrow text-ink-muted hover:text-amber"
    >
      ← Back to exploration tasks
    </Link>
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
