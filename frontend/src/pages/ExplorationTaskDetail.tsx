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
import { MetricStat } from '@/components/ui/MetricStat'
import { ExplorationTaskStatusBadge } from '@/components/features/exploration-tasks/ExplorationTaskStatusBadge'
import {
  useAbandonExplorationTask,
  useExplorationTask,
} from '@/hooks/useExplorationTasks'
import { usePortfolios } from '@/hooks/usePortfolio'
import { formatDate, formatNumber, formatPercent } from '@/utils/formatters'
import { extractTaskBody, extractTaskTitle } from '@/utils/explorationTaskTitle'
import type {
  ExplorationFindingsComparisonResponse,
  ExplorationFindingsMetricsResponse,
  ExplorationTaskResponse,
} from '@/services/api/types'

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

            {/* Recommended-strategy banner — Phase E2 structured payload */}
            {task.findings.recommended_strategy_id && (
              <RecommendedStrategyBanner
                strategyId={task.findings.recommended_strategy_id}
                parameters={task.findings.recommended_parameters}
              />
            )}

            {/* Confidence — Phase E2 */}
            {task.findings.confidence !== null && (
              <ConfidenceBar value={task.findings.confidence} />
            )}

            {/* Metrics — Phase E2 */}
            {task.findings.metrics && (
              <FindingsMetricsBlock metrics={task.findings.metrics} />
            )}

            {/* Comparison to baseline — Phase E2 */}
            {task.findings.comparison_to_baseline && (
              <ComparisonToBaselineTable
                comparison={task.findings.comparison_to_baseline}
              />
            )}

            {/* Narrative summary — still the readable wrapper, kept
                prominent below the structured fields. */}
            <div
              className="mt-6"
              data-testid="exploration-task-detail-findings-summary-section"
            >
              <Eyebrow>Summary</Eyebrow>
              <p
                className="mt-2 font-sans text-body-md text-ink whitespace-pre-wrap leading-relaxed"
                data-testid="exploration-task-detail-findings-summary"
              >
                {task.findings.summary}
              </p>
            </div>

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

/**
 * Renders a key/value list for the agent's chosen parameter combination.
 * The shape varies per strategy type (MA-crossover has different keys
 * from DCA), so we just render the dict as-is. Object values render as
 * a nested key/value list (one level of nesting handles the common
 * "allocation: {AAPL: 1.0}" case for buy-and-hold).
 */
function ParameterList({
  parameters,
}: {
  parameters: Record<string, unknown>
}): React.JSX.Element {
  const entries = Object.entries(parameters)
  if (entries.length === 0) {
    return (
      <span
        className="text-ink-subtle font-tabular text-body-sm"
        data-testid="exploration-task-detail-parameters-empty"
      >
        No parameters
      </span>
    )
  }
  return (
    <dl
      className="grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]"
      data-testid="exploration-task-detail-parameters"
    >
      {entries.map(([key, value]) => (
        <div
          key={key}
          className="contents"
          data-testid={`exploration-task-detail-param-${key}`}
        >
          <dt className="font-eyebrow text-ink-subtle">{key}</dt>
          <dd className="font-tabular text-body-sm text-ink">
            {renderParameterValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function renderParameterValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object' && !Array.isArray(value)) {
    // Nested dict — render inline as "k=v, k=v" so callers can scan it
    // without growing the visual hierarchy.
    const inner = Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k}=${String(v)}`)
      .join(', ')
    return inner.length > 0 ? `{${inner}}` : '{}'
  }
  if (Array.isArray(value)) return value.map((v) => String(v)).join(', ')
  return String(value)
}

/**
 * Banner highlighting the agent's recommended strategy + its parameter
 * combination (Phase E2). The strategy ID renders as a non-link mono
 * text — there is no detail page yet, but it's still the recommendation
 * stamp at the top of the findings panel.
 */
function RecommendedStrategyBanner({
  strategyId,
  parameters,
}: {
  strategyId: string
  parameters: Record<string, unknown> | null
}): React.JSX.Element {
  return (
    <div
      className="mt-4 rounded-editorial border border-amber/40 bg-amber-soft/30 p-4"
      data-testid="exploration-task-detail-recommended"
    >
      <Eyebrow tone="accent">Recommended</Eyebrow>
      <div className="mt-1 flex flex-col gap-3 sm:flex-row sm:items-baseline sm:gap-6">
        <span
          className="font-tabular text-body-sm text-ink"
          data-testid="exploration-task-detail-recommended-strategy-id"
        >
          {strategyId}
        </span>
      </div>
      {parameters !== null && (
        <div className="mt-3">
          <ParameterList parameters={parameters} />
        </div>
      )}
    </div>
  )
}

/**
 * Visual progress bar for the agent's confidence in the recommendation
 * (Phase E2). Renders as a small amber-filled track + a percentage
 * label. Out-of-range values are clamped to [0, 1] to keep the bar
 * stable even if the backend somehow lets through an invalid value.
 */
function ConfidenceBar({ value }: { value: number }): React.JSX.Element {
  const clamped = Math.max(0, Math.min(1, value))
  const percentLabel = `${Math.round(clamped * 100)}%`
  return (
    <div className="mt-5" data-testid="exploration-task-detail-confidence">
      <div className="flex items-baseline justify-between">
        <Eyebrow>Confidence</Eyebrow>
        <span
          className="font-tabular text-body-sm text-ink-muted"
          data-testid="exploration-task-detail-confidence-label"
        >
          {percentLabel}
        </span>
      </div>
      <div
        className="mt-2 h-2 w-full overflow-hidden rounded-editorial bg-canvas-sunken border border-hairline"
        role="progressbar"
        aria-valuenow={Math.round(clamped * 100)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Agent confidence"
      >
        <div
          className="h-full bg-amber"
          data-testid="exploration-task-detail-confidence-fill"
          style={{ width: `${clamped * 100}%` }}
        />
      </div>
    </div>
  )
}

function metricTone(value: number | null): 'neutral' | 'gain' | 'loss' {
  if (value === null) return 'neutral'
  return value >= 0 ? 'gain' : 'loss'
}

/**
 * Renders the structured metric block (Phase E2) using `MetricStat`
 * primitives. Decimal values arrive as wire strings (e.g. "24.4" means
 * +24.4%) — same convention as `BacktestRun` metrics.
 */
function FindingsMetricsBlock({
  metrics,
}: {
  metrics: ExplorationFindingsMetricsResponse
}): React.JSX.Element {
  // Wire decimals are percent-already (e.g. "24.4" = 24.4%); divide by 100
  // because formatPercent expects a fraction (0.244 = 24.40%).
  const totalReturn = parseFloat(metrics.total_return_pct) / 100
  const annualizedReturn =
    metrics.annualized_return_pct !== null
      ? parseFloat(metrics.annualized_return_pct) / 100
      : null
  const maxDrawdown =
    metrics.max_drawdown_pct !== null
      ? parseFloat(metrics.max_drawdown_pct) / 100
      : null
  const sharpe =
    metrics.sharpe_ratio !== null ? parseFloat(metrics.sharpe_ratio) : null

  return (
    <div className="mt-5" data-testid="exploration-task-detail-metrics">
      <Eyebrow>Metrics</Eyebrow>
      <div className="mt-3 grid grid-cols-2 gap-x-6 gap-y-6 sm:grid-cols-4 lg:grid-cols-5">
        <MetricStat
          label="Total return"
          value={formatPercent(totalReturn)}
          size="sm"
          tone={metricTone(totalReturn)}
          testId="metric-finding-total-return"
        />
        {sharpe !== null && (
          <MetricStat
            label="Sharpe"
            value={formatNumber(sharpe)}
            size="sm"
            tone={metricTone(sharpe)}
            testId="metric-finding-sharpe"
          />
        )}
        {maxDrawdown !== null && (
          <MetricStat
            label="Max drawdown"
            value={formatPercent(maxDrawdown, false)}
            size="sm"
            tone={maxDrawdown < 0 ? 'loss' : 'neutral'}
            testId="metric-finding-max-drawdown"
          />
        )}
        {annualizedReturn !== null && (
          <MetricStat
            label="Annualized"
            value={formatPercent(annualizedReturn)}
            size="sm"
            tone={metricTone(annualizedReturn)}
            testId="metric-finding-annualized"
          />
        )}
        {metrics.n_trades !== null && (
          <MetricStat
            label="Trades"
            value={String(metrics.n_trades)}
            size="sm"
            testId="metric-finding-n-trades"
          />
        )}
      </div>
    </div>
  )
}

/**
 * Comparison-to-baseline table (Phase E2). Shows total-return and Sharpe
 * deltas with gain/loss tones. The baseline strategy ID is rendered as a
 * mono identifier (no detail page yet).
 */
function ComparisonToBaselineTable({
  comparison,
}: {
  comparison: ExplorationFindingsComparisonResponse
}): React.JSX.Element {
  const baselineReturn = parseFloat(comparison.baseline_total_return_pct) / 100
  const deltaReturn = parseFloat(comparison.delta_total_return_pct) / 100
  const deltaSharpe =
    comparison.delta_sharpe !== null
      ? parseFloat(comparison.delta_sharpe)
      : null

  return (
    <div className="mt-5" data-testid="exploration-task-detail-comparison">
      <Eyebrow>vs baseline</Eyebrow>
      <table className="mt-2 w-full border-collapse text-body-sm">
        <thead>
          <tr className="text-left">
            <th className="border-b border-hairline pb-1 pr-4 font-eyebrow font-normal text-ink-subtle">
              Metric
            </th>
            <th className="border-b border-hairline pb-1 pr-4 font-eyebrow font-normal text-ink-subtle">
              Baseline
            </th>
            <th className="border-b border-hairline pb-1 font-eyebrow font-normal text-ink-subtle">
              Δ
            </th>
          </tr>
        </thead>
        <tbody className="font-tabular text-ink">
          <tr>
            <td className="py-2 pr-4 text-ink-muted">Total return</td>
            <td className="py-2 pr-4">{formatPercent(baselineReturn)}</td>
            <td
              className={`py-2 ${deltaReturn >= 0 ? 'text-gain' : 'text-loss'}`}
              data-testid="exploration-task-detail-comparison-delta-return"
            >
              {formatPercent(deltaReturn)}
            </td>
          </tr>
          {deltaSharpe !== null && (
            <tr>
              <td className="py-2 pr-4 text-ink-muted">Sharpe</td>
              <td className="py-2 pr-4 text-ink-muted">—</td>
              <td
                className={`py-2 ${deltaSharpe >= 0 ? 'text-gain' : 'text-loss'}`}
                data-testid="exploration-task-detail-comparison-delta-sharpe"
              >
                {formatNumber(deltaSharpe)}
              </td>
            </tr>
          )}
        </tbody>
      </table>
      <div
        className="mt-2 font-tabular text-body-sm text-ink-subtle"
        data-testid="exploration-task-detail-comparison-baseline-id"
      >
        Baseline strategy: {comparison.baseline_strategy_id}
      </div>
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
