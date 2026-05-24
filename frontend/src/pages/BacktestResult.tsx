/**
 * BacktestResult page — single backtest run detail.
 *
 * Layout:
 *   - Top nav row with a quiet "Backtests" back link and the status badge.
 *   - Editorial header (eyebrow + serif name + date-range caption).
 *   - Hairline rule.
 *   - Performance metrics grid.
 *   - Performance chart, sectioned with its own SectionHeader.
 *   - Agent invocations log (Phase L-4) — only when agent_invocation_mode != 'none'.
 *   - Failed-state error block uses the muted loss palette.
 */
import { Link, useParams } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { SectionHeader } from '@/components/ui/SectionHeader'
import {
  BacktestMetrics,
  BacktestStatusBadge,
} from '@/components/features/backtests/BacktestMetrics'
import { AgentInvocationsSection } from '@/components/features/backtests/AgentInvocationsSection'
import { PerformanceChart } from '@/components/features/analytics/PerformanceChart'
import { useBacktest } from '@/hooks/useBacktests'
import { formatDate } from '@/utils/formatters'

export function BacktestResult(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const backtestId = id ?? ''
  const { data: backtest, isLoading, error } = useBacktest(backtestId)

  if (isLoading) {
    return (
      <PageFrame>
        <div data-testid="backtest-result-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      </PageFrame>
    )
  }

  if (error || !backtest) {
    return (
      <PageFrame>
        <div
          data-testid="backtest-result-error"
          className="rounded-editorial border border-hairline bg-loss-soft/40 p-6"
        >
          <Eyebrow className="text-loss">Error</Eyebrow>
          <p className="mt-2 text-body-md text-ink">
            Failed to load backtest. It may have been deleted or does not exist.
          </p>
        </div>
        <div className="mt-6">
          <Link
            to="/backtests"
            className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink text-body-sm transition-colors"
            style={{ minHeight: 'auto' }}
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Back to backtests
          </Link>
        </div>
      </PageFrame>
    )
  }

  return (
    <PageFrame>
      {/* Top nav row */}
      <div
        className="flex flex-wrap items-center justify-between gap-3 reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
      >
        <Link
          to="/backtests"
          data-testid="back-to-backtests"
          className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink text-body-sm transition-colors"
          style={{ minHeight: 'auto' }}
        >
          <ArrowLeft className="h-3.5 w-3.5" /> Backtests
        </Link>
        <BacktestStatusBadge status={backtest.status} />
      </div>

      {/* Editorial header */}
      <header
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '60ms' }}
      >
        <Eyebrow>Backtest</Eyebrow>
        <h1
          className="mt-1 font-display text-display-md sm:text-display-lg tracking-tight text-ink"
          data-testid="backtest-name"
        >
          {backtest.backtest_name}
        </h1>
        <p
          className="mt-3 font-tabular text-body-sm text-ink-muted"
          data-testid="backtest-date-range-header"
        >
          {formatDate(backtest.start_date, false)} –{' '}
          {formatDate(backtest.end_date, false)}
        </p>
      </header>

      {/* Hairline rule */}
      <div
        className="mt-6 sm:mt-8 border-t border-hairline reveal"
        style={{ ['--reveal-delay' as string]: '90ms' }}
      />

      {/* Failed error message */}
      {backtest.status === 'FAILED' && backtest.error_message && (
        <div
          className="mt-6 rounded-editorial border border-hairline bg-loss-soft/40 p-5 reveal"
          style={{ ['--reveal-delay' as string]: '120ms' }}
        >
          <Eyebrow className="text-loss">Backtest failed</Eyebrow>
          <p
            className="mt-2 text-body-sm text-ink"
            data-testid="backtest-error-message"
          >
            {backtest.error_message}
          </p>
        </div>
      )}

      {/* Metrics */}
      <div
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '180ms' }}
      >
        <BacktestMetrics backtest={backtest} />
      </div>

      {/* Performance chart */}
      <section
        className="mt-12 sm:mt-16 reveal"
        style={{ ['--reveal-delay' as string]: '240ms' }}
      >
        <SectionHeader
          eyebrow="Trajectory"
          title="Portfolio value over time"
          size="sm"
        />
        <PerformanceChart
          portfolioId={backtest.portfolio_id}
          backtestStartDate={backtest.start_date}
          initialCash={parseFloat(backtest.initial_cash)}
        />
      </section>

      {/* Agent invocations — Phase L-4 (Task #220). Only rendered for
          runs with `agent_invocation_mode !== 'none'`. The section
          renders its own loading / empty / error states. Older API
          servers may omit the field; we treat undefined as `'none'`. */}
      {backtest.agent_invocation_mode !== undefined &&
        backtest.agent_invocation_mode !== 'none' && (
          <AgentInvocationsSection
            backtestId={backtest.id}
            agentInvocationMode={backtest.agent_invocation_mode}
          />
        )}
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
