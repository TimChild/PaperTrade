import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePortfolios, usePortfolioBalance } from '@/hooks/usePortfolio'
import { PortfolioCard } from '@/components/features/portfolio/PortfolioCard'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ErrorDisplay } from '@/components/ui/ErrorDisplay'
import { EmptyState } from '@/components/ui/EmptyState'
import { Dialog } from '@/components/ui/Dialog'
import { CreatePortfolioForm } from '@/components/features/portfolio/CreatePortfolioForm'
import { adaptPortfolio } from '@/utils/adapters'
import type { PortfolioDTO } from '@/services/api/types'

/**
 * Component that fetches balance for a single portfolio and renders the card
 */
function PortfolioCardWithBalance({ portfolioDTO }: { portfolioDTO: PortfolioDTO }) {
  const { data: balanceData } = usePortfolioBalance(portfolioDTO.id)
  const portfolio = adaptPortfolio(portfolioDTO, balanceData || null)
  
  return <PortfolioCard portfolio={portfolio} isLoading={!balanceData} />
}

export function Dashboard(): React.JSX.Element {
  const [showCreateModal, setShowCreateModal] = useState(false)
  const navigate = useNavigate()
  const { data: portfolios, isLoading: portfoliosLoading, isError, error } = usePortfolios()

  if (isError) {
    return (
      <div className="container mx-auto px-4 py-8">
        <ErrorDisplay error={error} />
      </div>
    )
  }

  // Show loading spinner while initial data loads
  if (portfoliosLoading) {
    return (
      <div className="container mx-auto px-4 py-8">
        <LoadingSpinner size="lg" className="py-12" />
      </div>
    )
  }

  return (
    <div className="container mx-auto px-4 py-8">
      <header className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-4xl font-bold text-gray-900 dark:text-white">
            Portfolio Dashboard
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            Track your investments and performance
          </p>
        </div>
        <button
          onClick={() => setShowCreateModal(true)}
          data-testid="create-portfolio-header-btn"
          className="rounded-lg bg-blue-600 px-4 py-2 font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          Create Portfolio
        </button>
      </header>

      <div className="space-y-8">
        {/* Portfolio Grid */}
        <section>
          {!portfolios || portfolios.length === 0 ? (
            <EmptyState
              message="No portfolios found. Create your first portfolio to get started!"
              action={
                <button
                  onClick={() => setShowCreateModal(true)}
                  data-testid="create-first-portfolio-btn"
                  className="rounded-lg bg-blue-600 px-6 py-3 font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
                >
                  Create Your First Portfolio
                </button>
              }
            />
          ) : (
            <>
              <div className="mb-6">
                <h2 className="text-2xl font-semibold text-gray-900 dark:text-white">
                  Your Portfolios
                </h2>
                <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">
                  You have {portfolios.length} portfolio{portfolios.length !== 1 ? 's' : ''}
                </p>
              </div>
              <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3" data-testid="portfolio-grid">
                {portfolios.map((portfolioDTO) => (
                  <PortfolioCardWithBalance key={portfolioDTO.id} portfolioDTO={portfolioDTO} />
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
  )
}
