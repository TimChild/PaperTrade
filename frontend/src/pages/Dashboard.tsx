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
import { adaptPortfolio } from '@/utils/adapters'
import type { PortfolioDTO } from '@/services/api/types'

/**
 * Component that fetches balance for a single portfolio and renders the card
 */
function PortfolioCardWithBalance({
  portfolioDTO,
}: {
  portfolioDTO: PortfolioDTO
}) {
  const { data: balanceData } = usePortfolioBalance(portfolioDTO.id)
  const portfolio = adaptPortfolio(portfolioDTO, balanceData || null)

  return <PortfolioCard portfolio={portfolio} isLoading={!balanceData} />
}

export function Dashboard(): React.JSX.Element {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const navigate = useNavigate()
  const {
    data: portfolios,
    isLoading: portfoliosLoading,
    isError,
    error,
  } = usePortfolios()

  if (isError) {
    return (
      <div className="min-h-screen bg-background-primary px-container-padding-x py-container-padding-y">
        <ErrorDisplay error={error} />
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-background-primary px-container-padding-x py-container-padding-y">
      <div className="max-w-7xl mx-auto">
        <header className="mb-12 flex items-center justify-between">
          <div>
            <h1 className="text-heading-xl text-foreground-primary mb-4">
              Portfolio Dashboard
            </h1>
            <p className="text-heading-md text-foreground-secondary">
              Track your investments and performance
            </p>
          </div>
          <Button
            onClick={() => setShowCreateModal(true)}
            data-testid="create-portfolio-header-btn"
          >
            Create Portfolio
          </Button>
        </header>

        <div className="space-y-8">
          {/* Portfolio Grid */}
          <section>
            {portfoliosLoading ? (
              <PortfolioListSkeleton />
            ) : !portfolios || portfolios.length === 0 ? (
              <EmptyState
                message="No portfolios found. Create your first portfolio to get started!"
                action={
                  <Button
                    onClick={() => setShowCreateModal(true)}
                    data-testid="create-first-portfolio-btn"
                    size="lg"
                  >
                    Create Your First Portfolio
                  </Button>
                }
              />
            ) : (
              <>
                <div className="mb-8">
                  <h2 className="text-heading-lg text-foreground-primary">
                    Your Portfolios
                  </h2>
                  <p className="mt-1 text-sm text-foreground-secondary">
                    You have {portfolios.length} portfolio
                    {portfolios.length !== 1 ? 's' : ''}
                  </p>
                </div>
                <div
                  className="grid gap-card-gap sm:grid-cols-2 lg:grid-cols-3"
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
        </div>

        {/* Portfolio Creation Modal */}
        <Dialog
          isOpen={showCreateModal}
          onClose={() => setShowCreateModal(false)}
          title="Create New Portfolio"
          className="max-w-md"
        >
          <CreatePortfolioForm
            onSuccess={(portfolioId) => {
              setShowCreateModal(false)
              // Navigate to the newly created portfolio so user can see it immediately
              navigate(`/portfolio/${portfolioId}`)
            }}
            onCancel={() => setShowCreateModal(false)}
          />
        </Dialog>
      </div>
    </div>
  )
}
