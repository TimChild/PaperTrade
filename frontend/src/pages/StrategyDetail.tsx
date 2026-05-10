/**
 * Strategy detail (Phase G-2).
 *
 * Hosts the per-strategy provenance section, ticker chips, parameters
 * preview, the live activation surface (re-used from the library card),
 * and an "Ask an agent" CTA that opens an exploration-task dialog
 * pre-filled with the strategy's tickers.
 *
 * The page is intentionally minimal — it's not a backtests dashboard or a
 * trade composer. Those surfaces live elsewhere (Backtests / Portfolio).
 */
import { Link, useParams } from 'react-router-dom'
import { useState } from 'react'
import { ArrowLeft } from 'lucide-react'
import { Caption } from '@/components/ui/Caption'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Panel } from '@/components/ui/Panel'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { StrategyActivationPanel } from '@/components/features/strategies/StrategyActivationPanel'
import { StrategyProvenanceSection } from '@/components/features/strategies/StrategyProvenanceSection'
import { AskAnAgentButton } from '@/components/features/exploration-tasks/AskAnAgentButton'
import { useStrategy } from '@/hooks/useStrategies'
import { formatDate } from '@/utils/formatters'
import type { StrategyType } from '@/services/api/types'

const STRATEGY_TYPE_LABELS: Record<StrategyType, string> = {
  BUY_AND_HOLD: 'Buy & Hold',
  DOLLAR_COST_AVERAGING: 'Dollar Cost Averaging',
  MOVING_AVERAGE_CROSSOVER: 'Moving Average Crossover',
}

export function StrategyDetail(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const strategyId = id ?? ''
  const { data: strategy, isLoading, error } = useStrategy(strategyId)
  const [askDialogKey, setAskDialogKey] = useState(0)

  if (isLoading) {
    return (
      <PageFrame>
        <div data-testid="strategy-detail-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      </PageFrame>
    )
  }

  if (error || !strategy) {
    return (
      <PageFrame>
        <BackLink />
        <div
          data-testid="strategy-detail-error"
          className="mt-6 rounded-editorial border border-hairline bg-loss-soft/40 p-6"
        >
          <Eyebrow tone="accent">Error</Eyebrow>
          <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
            Failed to load this strategy
          </h2>
          <p className="mt-2 text-body-sm text-ink-muted">
            Try refreshing the page. If the problem persists, the strategy may
            have been deleted.
          </p>
        </div>
      </PageFrame>
    )
  }

  return (
    <PageFrame>
      <BackLink />

      <header
        className="mt-4 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="strategy-detail-page"
      >
        <Eyebrow>Strategy</Eyebrow>
        <div className="mt-2 flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between sm:gap-6">
          <h1
            className="font-display text-display-md sm:text-display-lg tracking-tight text-ink max-w-3xl"
            data-testid="strategy-detail-name"
          >
            {strategy.name}
          </h1>
          <div className="flex flex-shrink-0 items-center gap-3">
            <span
              className="inline-flex items-center font-eyebrow rounded-editorial bg-canvas-raised border border-hairline px-2 py-1 text-ink-muted"
              data-testid="strategy-detail-type-badge"
            >
              {STRATEGY_TYPE_LABELS[strategy.strategy_type]}
            </span>
            {/* Editorial: an amber-outlined secondary CTA. Quiet next to
                the strategy type chip; remounts via key so its dialog
                seeds the latest tickers. */}
            <AskAnAgentButton
              key={askDialogKey}
              data-testid="ask-an-agent-strategy-btn"
              initialTickers={strategy.tickers}
              triggerContext="strategy"
              onSubmitted={() => setAskDialogKey((k) => k + 1)}
            />
          </div>
        </div>
        <Caption className="mt-3 block text-ink-subtle">
          Created {formatDate(strategy.created_at, true)}
        </Caption>
      </header>

      <section
        className="mt-8 reveal"
        style={{ ['--reveal-delay' as string]: '60ms' }}
      >
        <StrategyProvenanceSection
          strategyId={strategy.id}
          createdAt={strategy.created_at}
        />
      </section>

      <section
        className="mt-6 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        <Panel>
          <Eyebrow>Tickers</Eyebrow>
          <div
            className="mt-3 flex flex-wrap gap-1.5"
            data-testid="strategy-detail-tickers"
          >
            {strategy.tickers.length === 0 ? (
              <span className="text-ink-subtle">No tickers</span>
            ) : (
              strategy.tickers.map((ticker) => (
                <span
                  key={ticker}
                  className="rounded-editorial bg-canvas-sunken border border-hairline px-2 py-0.5 font-tabular text-body-sm text-ink"
                >
                  {ticker}
                </span>
              ))
            )}
          </div>
        </Panel>
      </section>

      <section
        className="mt-6 reveal"
        style={{ ['--reveal-delay' as string]: '180ms' }}
      >
        <Panel>
          <Eyebrow>Live activation</Eyebrow>
          <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
            Scheduler binding
          </h2>
          <div className="mt-4">
            <StrategyActivationPanel strategy={strategy} />
          </div>
        </Panel>
      </section>

      <section
        className="mt-6 reveal"
        style={{ ['--reveal-delay' as string]: '240ms' }}
      >
        <Panel>
          <SectionHeader
            eyebrow="Parameters"
            title="Strategy configuration"
            size="sm"
            description="The parameters the strategy was created with. Values are immutable post-creation — create a new strategy if you need different parameters."
          />
          <ParameterPreview parameters={strategy.parameters} />
        </Panel>
      </section>
    </PageFrame>
  )
}

/**
 * Renders the strategy.parameters dict as a key/value list. Shape varies
 * by strategy type — we render the raw dict rather than per-type renderers
 * since the values are typically scalars or one-level-deep dicts.
 */
function ParameterPreview({
  parameters,
}: {
  parameters: Record<string, unknown>
}): React.JSX.Element {
  const entries = Object.entries(parameters)
  if (entries.length === 0) {
    return (
      <p
        className="mt-3 text-body-sm text-ink-subtle"
        data-testid="strategy-detail-parameters-empty"
      >
        No parameters set.
      </p>
    )
  }
  return (
    <dl
      className="mt-3 grid grid-cols-1 gap-x-4 gap-y-1 sm:grid-cols-[max-content_1fr]"
      data-testid="strategy-detail-parameters"
    >
      {entries.map(([key, value]) => (
        <div key={key} className="contents">
          <dt className="font-eyebrow text-ink-subtle">{key}</dt>
          <dd className="font-tabular text-body-sm text-ink">
            {renderValue(value)}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function renderValue(value: unknown): React.ReactNode {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'object' && !Array.isArray(value)) {
    const inner = Object.entries(value as Record<string, unknown>)
      .map(([k, v]) => `${k}=${String(v)}`)
      .join(', ')
    return inner.length > 0 ? `{${inner}}` : '{}'
  }
  if (Array.isArray(value)) return value.map((v) => String(v)).join(', ')
  return String(value)
}

function BackLink(): React.JSX.Element {
  return (
    <Link
      to="/strategies"
      data-testid="strategy-detail-back-link"
      className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink text-body-sm transition-colors"
      style={{ minHeight: 'auto' }}
    >
      <ArrowLeft className="h-3.5 w-3.5" /> Strategies
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
