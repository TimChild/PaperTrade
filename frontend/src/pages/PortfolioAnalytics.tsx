/**
 * Portfolio Analytics — editorial drilldown into a portfolio's performance
 * over time. Sections (eyebrow + serif heading) separate the metric grid,
 * value-over-time chart, composition-over-time stacked area, and the
 * holdings pie. No card chrome around the charts.
 */
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { usePortfolio } from '@/hooks/usePortfolio'
import { PerformanceChart } from '@/components/features/analytics/PerformanceChart'
import { CompositionChart } from '@/components/features/analytics/CompositionChart'
import { MetricsCards } from '@/components/features/analytics/MetricsCards'
import { CompositionOverTimeChart } from '@/components/features/analytics/CompositionOverTimeChart'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { SectionHeader } from '@/components/ui/SectionHeader'

export function PortfolioAnalytics(): React.JSX.Element {
  const { id } = useParams<{ id: string }>()
  const portfolioId = id || ''

  const { data: portfolio, isLoading, error } = usePortfolio(portfolioId)

  if (isLoading) {
    return (
      <PageFrame>
        <div className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      </PageFrame>
    )
  }

  if (error) {
    return (
      <PageFrame>
        <ErrorDisplay error={error} />
        <div className="mt-6">
          <BackLink portfolioId={portfolioId} />
        </div>
      </PageFrame>
    )
  }

  if (!portfolioId) {
    return (
      <PageFrame>
        <div className="rounded-editorial border border-hairline bg-loss-soft/40 p-6">
          <Eyebrow className="text-loss">Not found</Eyebrow>
          <p className="mt-2 text-body-md text-ink">Portfolio not found.</p>
        </div>
        <div className="mt-6">
          <BackLink portfolioId="" />
        </div>
      </PageFrame>
    )
  }

  return (
    <PageFrame>
      <div
        className="reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="portfolio-analytics"
      >
        <BackLink portfolioId={portfolioId} />
      </div>

      <header
        className="mt-6 sm:mt-8 reveal"
        style={{ ['--reveal-delay' as string]: '60ms' }}
      >
        <Eyebrow>Analytics</Eyebrow>
        <h1 className="mt-1 font-display text-display-md sm:text-display-lg tracking-tight text-ink">
          {portfolio?.name}
        </h1>
      </header>

      {/* Hairline rule */}
      <div
        className="mt-6 sm:mt-8 border-t border-hairline reveal"
        style={{ ['--reveal-delay' as string]: '90ms' }}
      />

      {/* Performance Summary — metrics grid */}
      <section
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        <SectionHeader
          eyebrow="Snapshot"
          title="Performance summary"
          size="sm"
        />
        <MetricsCards portfolioId={portfolioId} />
      </section>

      {/* Performance Chart */}
      <section
        className="mt-12 sm:mt-16 reveal"
        style={{ ['--reveal-delay' as string]: '180ms' }}
      >
        <SectionHeader
          eyebrow="Trajectory"
          title="Portfolio value over time"
          size="sm"
        />
        <PerformanceChart portfolioId={portfolioId} />
      </section>

      {/* Composition Over Time */}
      <section
        className="mt-12 sm:mt-16 reveal"
        style={{ ['--reveal-delay' as string]: '240ms' }}
      >
        <SectionHeader
          eyebrow="Allocation"
          title="Composition over time"
          size="sm"
          description="Stacked cash and per-ticker holdings, evaluated at each daily snapshot."
        />
        <CompositionOverTimeChart portfolioId={portfolioId} />
      </section>

      {/* Composition pie */}
      <section
        className="mt-12 sm:mt-16 reveal"
        style={{ ['--reveal-delay' as string]: '300ms' }}
      >
        <SectionHeader
          eyebrow="Allocation"
          title="Holdings composition"
          size="sm"
          description="Today's allocation across cash and each open position."
        />
        <CompositionChart portfolioId={portfolioId} />
      </section>
    </PageFrame>
  )
}

interface BackLinkProps {
  portfolioId: string
}

function BackLink({ portfolioId }: BackLinkProps): React.JSX.Element {
  return (
    <Link
      to={portfolioId ? `/portfolio/${portfolioId}` : '/dashboard'}
      data-testid="analytics-back-link"
      className="inline-flex items-center gap-1.5 text-ink-muted hover:text-ink text-body-sm transition-colors"
      style={{ minHeight: 'auto' }}
    >
      <ArrowLeft className="h-3.5 w-3.5" />
      {portfolioId ? 'Portfolio' : 'Dashboard'}
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
