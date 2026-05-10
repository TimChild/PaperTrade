import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePortfolios, usePortfolioBalance } from '@/hooks/usePortfolio'
import { PortfolioCard } from '@/components/features/portfolio/PortfolioCard'
import { PortfolioListSkeleton } from '@/components/features/portfolio/PortfolioListSkeleton'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'
import { EmptyState } from '@/components/ui/EmptyState'
import { Dialog } from '@/components/ui/Dialog'
import { Button } from '@/components/ui/button'
import { CreatePortfolioForm } from '@/components/features/portfolio/CreatePortfolioForm'
import { ThemeToggle } from '@/components/ui/theme-toggle'
import { SectionHeader } from '@/components/ui/SectionHeader'
import { adaptPortfolio } from '@/utils/adapters'
import type { PortfolioDTO } from '@/services/api/types'

/**
 * Dashboard — editorial multi-portfolio overview.
 *
 * Layout:
 *   - Section header (eyebrow + serif heading) introduces the page.
 *   - A hairline divider separates header from content.
 *   - Portfolios render as a 1/2/3 column grid of editorial PortfolioCards.
 *   - The "Create Portfolio" CTA lives in the header trailing slot — quiet,
 *     not the dominant moment on the page (the portfolios themselves are).
 */

function PortfolioCardWithBalance({
  portfolioDTO,
}: {
  portfolioDTO: PortfolioDTO
}): React.JSX.Element {
  const { data: balanceData } = usePortfolioBalance(portfolioDTO.id)
  const portfolio = adaptPortfolio(portfolioDTO, balanceData || null)

  return <PortfolioCard portfolio={portfolio} isLoading={!balanceData} />
}

export function Dashboard(): React.JSX.Element {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const navigate = useNavigate()
  const {
    data: portfoliosPage,
    isLoading: portfoliosLoading,
    isError,
    error,
  } = usePortfolios()
  const portfolios = portfoliosPage?.items

  if (isError) {
    return (
      <PageFrame>
        <ErrorDisplay error={error} />
      </PageFrame>
    )
  }

  return (
    <PageFrame>
      <div className="reveal" style={{ ['--reveal-delay' as string]: '0ms' }}>
        <SectionHeader
          eyebrow="Dashboard"
          title="Portfolios"
          as="h1"
          description="Track positions, performance, and cash across each paper-trading portfolio."
          trailing={
            <div className="flex items-center gap-3">
              <ThemeToggle />
              <Button
                onClick={() => setShowCreateModal(true)}
                data-testid="create-portfolio-header-btn"
              >
                Create portfolio
              </Button>
            </div>
          }
          withRule
        />
      </div>

      <section
        className="mt-8 sm:mt-10 reveal"
        style={{ ['--reveal-delay' as string]: '120ms' }}
      >
        {portfoliosLoading ? (
          <PortfolioListSkeleton />
        ) : !portfolios || portfolios.length === 0 ? (
          <EmptyState
            eyebrow="No portfolios yet"
            title="Start with your first portfolio"
            description="Create a paper-trading portfolio with starting cash and begin practicing trades."
            action={
              <Button
                onClick={() => setShowCreateModal(true)}
                data-testid="create-first-portfolio-btn"
                size="lg"
              >
                Create your first portfolio
              </Button>
            }
          />
        ) : (
          <>
            <div className="mb-6 flex items-baseline justify-between">
              <p
                className="font-eyebrow text-ink-muted"
                data-testid="portfolio-count-label"
              >
                {portfolios.length} portfolio
                {portfolios.length !== 1 ? 's' : ''}
              </p>
            </div>
            <div
              className="grid gap-5 sm:gap-6 grid-cols-1 sm:grid-cols-2 lg:grid-cols-3"
              data-testid="portfolio-grid"
            >
              {portfolios.map((portfolioDTO) => (
                <PortfolioCardWithBalance
                  key={portfolioDTO.id}
                  portfolioDTO={portfolioDTO}
                />
              ))}
            </div>
          </>
        )}
      </section>

      <Dialog
        isOpen={showCreateModal}
        onClose={() => setShowCreateModal(false)}
        title="New portfolio"
        eyebrow="Create"
        className="max-w-md w-[90vw]"
      >
        <CreatePortfolioForm
          onSuccess={(portfolioId) => {
            setShowCreateModal(false)
            navigate(`/portfolio/${portfolioId}`)
          }}
          onCancel={() => setShowCreateModal(false)}
        />
      </Dialog>
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
