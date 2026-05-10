/**
 * Compare backtests page — overlay normalized % return chart + metrics
 * comparison table. Editorial layout: section headers (no card chrome)
 * separate the chart from the table.
 */
import { Link, useSearchParams } from 'react-router-dom'
import { useQueries } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { ComparisonChart } from '@/components/features/backtests/ComparisonChart'
import { ComparisonTable } from '@/components/features/backtests/ComparisonTable'
import { useStrategies } from '@/hooks/useStrategies'
import { backtestsApi } from '@/services/api/backtests'
import { analyticsApi } from '@/services/api/analytics'

export function CompareBacktests(): React.JSX.Element {
  const [searchParams] = useSearchParams()
  const idsParam = searchParams.get('ids') ?? ''
  const ids = idsParam
    .split(',')
    .map((id) => id.trim())
    .filter(Boolean)

  const { data: strategiesPage } = useStrategies()
  const strategies = strategiesPage?.items

  const strategyNames: Record<string, string> = {}
  strategies?.forEach((s) => {
    strategyNames[s.id] = s.name
  })

  const backtestQueries = useQueries({
    queries: ids.map((id) => ({
      queryKey: ['backtests', id],
      queryFn: () => backtestsApi.getById(id),
      staleTime: 30_000,
      enabled: Boolean(id),
    })),
  })

  const loadedBacktests = backtestQueries
    .map((q) => q.data)
    .filter((b) => b !== undefined)

  const performanceQueries = useQueries({
    queries: loadedBacktests.map((b) => ({
      queryKey: ['performance', b.portfolio_id, 'ALL'],
      queryFn: () => analyticsApi.getPerformance(b.portfolio_id, 'ALL'),
      staleTime: 5 * 60 * 1000,
      enabled: Boolean(b.portfolio_id),
    })),
  })

  const isLoadingBacktests = backtestQueries.some((q) => q.isLoading)
  const isLoadingPerformance =
    loadedBacktests.length > 0 && performanceQueries.some((q) => q.isLoading)
  const isLoading = isLoadingBacktests || isLoadingPerformance

  const performanceSeries = loadedBacktests
    .map((b, i) => {
      const perfData = performanceQueries[i]?.data
      if (!perfData) return null
      return {
        name: b.backtest_name,
        data: perfData.data_points.map((d) => ({
          date: d.date,
          total_value: d.total_value,
        })),
      }
    })
    .filter(
      (
        entry
      ): entry is {
        name: string
        data: { date: string; total_value: number }[]
      } => entry !== null
    )

  if (ids.length === 0) {
    return (
      <PageFrame>
        <BackLink />
        <p className="mt-8 text-body-md text-ink-muted">
          No backtest IDs provided. Please select backtests to compare.
        </p>
      </PageFrame>
    )
  }

  return (
    <PageFrame>
      <div
        className="reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="compare-backtests-page"
      >
        <BackLink />
      </div>

      <header
        className="mt-6 sm:mt-8 reveal"
        style={{ ['--reveal-delay' as string]: '60ms' }}
      >
        <SectionHeader
          eyebrow="Comparison"
          title="Compare backtests"
          as="h1"
          description={`Side-by-side analysis of ${ids.length} backtest run${ids.length === 1 ? '' : 's'}.`}
          withRule
        />
      </header>

      {isLoading && (
        <div data-testid="compare-loading" className="py-12">
          <LoadingSpinner size="lg" />
          <p className="mt-4 text-center text-body-sm text-ink-muted">
            Loading backtest data…
          </p>
        </div>
      )}

      {!isLoading && (
        <>
          <section
            className="mt-8 sm:mt-10 reveal"
            style={{ ['--reveal-delay' as string]: '120ms' }}
          >
            <SectionHeader
              eyebrow="Trajectory"
              title="Normalized performance"
              size="sm"
              description="Each series rebased to 0% at its first data point."
            />
            <ComparisonChart series={performanceSeries} />
          </section>

          <section
            className="mt-12 sm:mt-16 reveal"
            style={{ ['--reveal-delay' as string]: '180ms' }}
          >
            <SectionHeader
              eyebrow="Metrics"
              title="Comparison table"
              size="sm"
              description="Best value highlighted in muted gain; worst in muted loss."
            />
            <ComparisonTable
              backtests={loadedBacktests}
              strategyNames={strategyNames}
            />
          </section>
        </>
      )}
    </PageFrame>
  )
}

function BackLink(): React.JSX.Element {
  return (
    <Link
      to="/backtests"
      data-testid="back-to-backtests"
      className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink text-body-sm transition-colors"
      style={{ minHeight: 'auto' }}
    >
      <ArrowLeft className="h-3.5 w-3.5" /> Backtests
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
