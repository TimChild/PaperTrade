/**
 * Activation detail page — Phase G-1.
 *
 * Centerpiece of Phase G: the human-facing surface for attaching triggers
 * to a live strategy activation. Layout:
 *
 *   - Back link to the activation list.
 *   - Hero: eyebrow + strategy name + status badge + creation/last-run captions.
 *   - Activation status panel (target portfolio, frequency, last error).
 *   - Triggers section (G-1) — the load-bearing new surface.
 *
 * The triggers section lives under `TriggersSection` so it composes cleanly
 * with future per-activation surfaces (e.g. activity drill-down in G-2).
 *
 * Routing: `/activations/:id`. Reached from the row click on the
 * `Activations.tsx` list view.
 */
import { Link, useParams } from 'react-router-dom'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { Caption } from '@/components/ui/Caption'
import { Panel } from '@/components/ui/Panel'
import { ActivationStatusBadge } from '@/components/features/strategies/ActivationStatusBadge'
import { TriggersSection } from '@/components/features/triggers/TriggersSection'
import { useActivationById } from '@/hooks/useStrategyActivation'
import { useStrategies } from '@/hooks/useStrategies'
import { usePortfolios } from '@/hooks/usePortfolio'
import { formatDate } from '@/utils/formatters'

function formatFrequency(freq: string): string {
  return freq.replace(/_/g, ' ').toLowerCase()
}

export function ActivationDetail(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const activationId = id ?? ''

  const { data: activation, isLoading, error } = useActivationById(activationId)
  const { data: strategiesPage } = useStrategies()
  const { data: portfoliosPage } = usePortfolios()

  if (isLoading) {
    return (
      <PageFrame>
        <div data-testid="activation-detail-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      </PageFrame>
    )
  }

  if (error || !activation) {
    return (
      <PageFrame>
        <BackLink />
        <div
          data-testid="activation-detail-error"
          className="mt-6 rounded-editorial border border-hairline bg-loss-soft/40 p-6"
        >
          <Eyebrow tone="accent">Not found</Eyebrow>
          <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
            This activation could not be found
          </h2>
          <p className="mt-2 text-body-sm text-ink-muted">
            It may have been removed, or you may not have permission to view it.
            Try heading back to the activations list.
          </p>
        </div>
      </PageFrame>
    )
  }

  const strategy = strategiesPage?.items.find(
    (s) => s.id === activation.strategy_id
  )
  const portfolio = portfoliosPage?.items.find(
    (p) => p.id === activation.portfolio_id
  )

  const headline = strategy?.name ?? `Activation ${activation.id.slice(0, 8)}`

  return (
    <PageFrame>
      <BackLink />

      {/* Hero */}
      <header
        className="mt-4 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="activation-detail-page"
      >
        <Eyebrow>Live execution · Activation</Eyebrow>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <h1
            className="font-display text-display-md sm:text-display-lg tracking-tight text-ink max-w-3xl"
            data-testid="activation-detail-title"
          >
            {headline}
          </h1>
          <div className="flex-shrink-0">
            <ActivationStatusBadge status={activation.status} />
          </div>
        </div>
        <Caption className="mt-3 block text-ink-subtle">
          Created {formatDate(activation.created_at, true)}
          {activation.last_executed_at && (
            <>
              {' · Last run '}
              {formatDate(activation.last_executed_at, true)}
            </>
          )}
        </Caption>
      </header>

      {/* Status panel — quick at-a-glance metadata */}
      <section
        className="mt-8 reveal"
        style={{ ['--reveal-delay' as string]: '60ms' }}
      >
        <Panel>
          <Eyebrow>Status</Eyebrow>
          <dl
            className="mt-4 grid gap-5 sm:grid-cols-3"
            data-testid="activation-detail-status"
          >
            <Field label="Target portfolio">
              {portfolio ? (
                <Link
                  to={`/portfolio/${portfolio.id}`}
                  className="text-amber underline-offset-4 hover:underline"
                  data-testid="activation-detail-portfolio-link"
                >
                  {portfolio.name}
                </Link>
              ) : (
                <span className="font-tabular text-ink-muted">
                  {activation.portfolio_id.slice(0, 8)}
                </span>
              )}
            </Field>
            <Field label="Frequency">
              <span className="text-body-md text-ink">
                {formatFrequency(activation.frequency)}
              </span>
            </Field>
            <Field label="Strategy">
              {strategy ? (
                <span className="text-body-md text-ink">{strategy.name}</span>
              ) : (
                <span className="font-tabular text-ink-muted">
                  {activation.strategy_id.slice(0, 8)}
                </span>
              )}
            </Field>
          </dl>

          {activation.status === 'ERROR' && activation.last_error && (
            <div
              className="mt-4 rounded-editorial border border-hairline bg-loss-soft/40 p-3"
              data-testid="activation-detail-last-error"
            >
              <Eyebrow tone="accent">Last error</Eyebrow>
              <p className="mt-1 text-body-sm text-ink whitespace-pre-wrap">
                {activation.last_error}
              </p>
            </div>
          )}

          {activation.status === 'PAUSED' && activation.deactivation_reason && (
            <div
              className="mt-4 rounded-editorial border border-hairline bg-amber-soft/40 p-3"
              data-testid="activation-detail-deactivation-reason"
            >
              <Eyebrow tone="accent">Paused — reason</Eyebrow>
              <p className="mt-1 text-body-sm text-ink whitespace-pre-wrap">
                {activation.deactivation_reason}
              </p>
            </div>
          )}
        </Panel>
      </section>

      {/* Triggers section — the G-1 centerpiece. */}
      <TriggersSection activationId={activation.id} />
    </PageFrame>
  )
}

function Field({
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
      to="/activations"
      data-testid="activation-detail-back-link"
      className="font-eyebrow text-ink-muted hover:text-amber"
    >
      ← Back to activations
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
