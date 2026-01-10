import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { usePortfolios, usePortfolioBalance } from '@/hooks/usePortfolio'
import { Dialog } from '@/components/ui/Dialog'
import { CreatePortfolioForm } from '@/components/features/portfolio/CreatePortfolioForm'
import { adaptPortfolio } from '@/utils/adapters'
import { formatCurrency, formatPercent } from '@/utils/formatters'
import type { PortfolioDTO } from '@/services/api/types'

/**
 * Component that fetches balance for a single portfolio and renders the card
 */
function PortfolioCardDataDense({
  portfolioDTO,
}: {
  portfolioDTO: PortfolioDTO
}) {
  const navigate = useNavigate()
  const { data: balanceData } = usePortfolioBalance(portfolioDTO.id)
  const portfolio = adaptPortfolio(portfolioDTO, balanceData || null)

  if (!balanceData) {
    return (
      <div className="rounded-lg border border-gray-700 bg-gray-800 p-4">
        <div className="animate-pulse space-y-3">
          <div className="h-5 w-32 rounded bg-gray-700"></div>
          <div className="h-6 w-24 rounded bg-gray-700"></div>
          <div className="h-4 w-20 rounded bg-gray-700"></div>
        </div>
      </div>
    )
  }

  const isPositiveChange = portfolio.dailyChange >= 0

  return (
    <div
      onClick={() => navigate(`/portfolio/${portfolio.id}`)}
      className="group cursor-pointer rounded-lg border border-gray-700 bg-gray-800 p-4 transition-colors hover:border-blue-500"
      data-testid={`portfolio-card-${portfolio.id}`}
    >
      {/* Portfolio Name - Compact */}
      <h2 className="mb-3 truncate text-base font-semibold text-gray-100">
        {portfolio.name}
      </h2>

      {/* Info Grid - Compact */}
      <div className="space-y-2 text-sm">
        {/* Total Value */}
        <div className="flex items-baseline justify-between">
          <span className="text-gray-400">Value</span>
          <span
            className="font-semibold text-gray-100"
            data-testid={`portfolio-card-value-${portfolio.id}`}
          >
            {formatCurrency(portfolio.totalValue, 'USD', 'compact')}
          </span>
        </div>

        {/* Cash Balance */}
        <div className="flex items-baseline justify-between">
          <span className="text-gray-400">Cash</span>
          <span className="font-medium text-gray-100">
            {formatCurrency(portfolio.cashBalance, 'USD', 'compact')}
          </span>
        </div>

        {/* Daily Change */}
        <div className="flex items-baseline justify-between border-t border-gray-700 pt-2">
          <span className="text-gray-400">Today</span>
          <div className="text-right">
            <div
              className={`font-semibold ${
                isPositiveChange ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {isPositiveChange ? '+' : ''}
              {formatCurrency(portfolio.dailyChange, 'USD', 'compact')}
            </div>
            <div
              className={`text-xs ${
                isPositiveChange ? 'text-green-400' : 'text-red-400'
              }`}
            >
              {formatPercent(portfolio.dailyChangePercent / 100)}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Dashboard Variant B: Data Dense
 *
 * Design characteristics:
 * - Bloomberg Terminal-inspired
 * - Compact spacing, efficient use of space
 * - Smaller typography, more info visible
 * - Subtle borders, less shadow emphasis
 * - Tighter grid (3-4 columns)
 * - Information-focused aesthetic
 */
export function DashboardVariantB(): React.JSX.Element {
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
      <div className="flex min-h-screen items-center justify-center bg-gray-900 px-4 py-6 text-gray-100">
        <div className="rounded-lg border border-red-700 bg-gray-800 p-6">
          <h2 className="mb-3 text-xl font-semibold text-red-400">Error</h2>
          <p className="text-sm text-gray-300">
            {error instanceof Error
              ? error.message
              : 'Failed to load portfolios'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-900 px-4 py-6 text-gray-100">
      <div className="mx-auto max-w-full">
        {/* Header - Compact */}
        <header className="mb-6 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-semibold text-gray-100">Portfolios</h1>
            {portfolios && portfolios.length > 0 && (
              <p className="mt-1 text-sm text-gray-400">
                {portfolios.length} active
              </p>
            )}
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            data-testid="create-portfolio-header-btn"
            className="rounded bg-blue-600 px-4 py-2 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            + New Portfolio
          </button>
        </header>

        {/* Portfolio Grid or Loading/Empty State */}
        {portfoliosLoading ? (
          <div className="grid gap-4 md:grid-cols-3 xl:grid-cols-4">
            {[1, 2, 3, 4, 5, 6, 7, 8].map((i) => (
              <div
                key={i}
                className="rounded-lg border border-gray-700 bg-gray-800 p-4"
              >
                <div className="animate-pulse space-y-3">
                  <div className="h-5 w-32 rounded bg-gray-700"></div>
                  <div className="h-6 w-24 rounded bg-gray-700"></div>
                  <div className="h-4 w-20 rounded bg-gray-700"></div>
                </div>
              </div>
            ))}
          </div>
        ) : !portfolios || portfolios.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-lg border border-gray-700 bg-gray-800 p-12">
            <div className="mb-6 text-center">
              <h2 className="mb-2 text-xl font-semibold text-gray-100">
                No Portfolios
              </h2>
              <p className="text-sm text-gray-400">
                Create a portfolio to start tracking investments
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              data-testid="create-first-portfolio-btn"
              className="rounded bg-blue-600 px-6 py-3 text-sm font-semibold text-white transition-colors hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              Create Portfolio
            </button>
          </div>
        ) : (
          // Dense Grid - 3-4 columns
          <div
            className="grid gap-4 md:grid-cols-3 xl:grid-cols-4"
            data-testid="portfolio-grid"
          >
            {portfolios.map((portfolioDTO) => (
              <PortfolioCardDataDense
                key={portfolioDTO.id}
                portfolioDTO={portfolioDTO}
              />
            ))}
          </div>
        )}
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
            navigate(`/portfolio/${portfolioId}`)
          }}
          onCancel={() => setShowCreateModal(false)}
        />
      </Dialog>
    </div>
  )
}
