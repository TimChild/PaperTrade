/**
 * Activations page — list of all the user's strategy activations.
 *
 * Phase C1.4 bonus: a top-level surface to see every active strategy at once,
 * independent of the strategy library. Each row exposes status, target
 * portfolio, frequency, and last-run timestamp.
 *
 * Editorial: hairline DataTable instead of the legacy gray-bordered table.
 */
import { Link, useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { EmptyState } from '@/components/ui/EmptyState'
import { SectionHeader } from '@/components/ui/SectionHeader'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataRow,
  DataCell,
  DataHeaderCell,
} from '@/components/ui/DataRow'
import { ActivationStatusBadge } from '@/components/features/strategies/ActivationStatusBadge'
import { useActivations } from '@/hooks/useStrategyActivation'
import { useStrategies } from '@/hooks/useStrategies'
import { usePortfolios } from '@/hooks/usePortfolio'
import { formatDate } from '@/utils/formatters'

function formatFrequency(freq: string): string {
  return freq.replace(/_/g, ' ').toLowerCase()
}

export function Activations(): React.JSX.Element {
  const navigate = useNavigate()
  const { data: activationsPage, isLoading, error } = useActivations()
  const { data: strategiesPage } = useStrategies()
  const { data: portfoliosPage } = usePortfolios()

  const activations = activationsPage?.items
  const strategyNames: Record<string, string> = {}
  strategiesPage?.items.forEach((s) => {
    strategyNames[s.id] = s.name
  })
  const portfolioNames: Record<string, string> = {}
  portfoliosPage?.items.forEach((p) => {
    portfolioNames[p.id] = p.name
  })

  return (
    <PageFrame>
      <div
        className="reveal"
        style={{ ['--reveal-delay' as string]: '0ms' }}
        data-testid="activations-page"
      >
        <SectionHeader
          eyebrow="Live execution"
          title="Activations"
          as="h1"
          description="Strategies currently set up to run live against your paper-trading portfolios."
          trailing={
            <Link to="/strategies">
              <Button
                variant="secondary"
                data-testid="activations-go-to-strategies"
              >
                Manage strategies
              </Button>
            </Link>
          }
          withRule
        />
      </div>

      <section
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        {isLoading && (
          <div data-testid="activations-loading" className="py-12">
            <LoadingSpinner size="lg" />
          </div>
        )}

        {error && !isLoading && (
          <div
            data-testid="activations-error"
            className="rounded-editorial border border-hairline bg-loss-soft/40 p-6 text-center"
          >
            <p className="text-body-md text-ink">
              Failed to load activations. Please try again.
            </p>
          </div>
        )}

        {!isLoading && !error && activations?.length === 0 && (
          <EmptyState
            data-testid="activations-empty"
            eyebrow="No live activations"
            title="No strategies are running yet"
            description="Activate a strategy from the library to begin running it daily after market close against a paper-trading portfolio."
            action={
              <Link to="/strategies">
                <Button>Go to strategies</Button>
              </Link>
            }
          />
        )}

        {!isLoading && !error && activations && activations.length > 0 && (
          <DataTable testId="activations-table">
            <DataTableHead>
              <DataHeaderCell>Strategy</DataHeaderCell>
              <DataHeaderCell>Status</DataHeaderCell>
              <DataHeaderCell hideOnMobile>Portfolio</DataHeaderCell>
              <DataHeaderCell hideUntilMd>Frequency</DataHeaderCell>
              <DataHeaderCell hideOnMobile>Last run</DataHeaderCell>
            </DataTableHead>
            <DataTableBody>
              {activations.map((a) => (
                <DataRow
                  key={a.id}
                  testId={`activation-row-${a.id}`}
                  interactive
                  onClick={() => void navigate(`/activations/${a.id}`)}
                >
                  <DataCell emphasis="primary">
                    {strategyNames[a.strategy_id] ?? a.strategy_id.slice(0, 8)}
                  </DataCell>
                  <DataCell>
                    <ActivationStatusBadge status={a.status} />
                  </DataCell>
                  <DataCell tone="muted" hideOnMobile>
                    {portfolioNames[a.portfolio_id] ??
                      a.portfolio_id.slice(0, 8)}
                  </DataCell>
                  <DataCell tone="muted" hideUntilMd>
                    {formatFrequency(a.frequency)}
                  </DataCell>
                  <DataCell tone="muted" numeric hideOnMobile>
                    {a.last_executed_at
                      ? formatDate(a.last_executed_at, true)
                      : 'Never'}
                  </DataCell>
                </DataRow>
              ))}
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
