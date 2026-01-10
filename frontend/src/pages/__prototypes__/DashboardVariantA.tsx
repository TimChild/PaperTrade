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
function PortfolioCardModernMinimal({
  portfolioDTO,
}: {
  portfolioDTO: PortfolioDTO
}) {
  const navigate = useNavigate()
  const { data: balanceData } = usePortfolioBalance(portfolioDTO.id)
  const portfolio = adaptPortfolio(portfolioDTO, balanceData || null)

  if (!balanceData) {
    return (
      <div className="rounded-2xl bg-white p-8 shadow-lg">
        <div className="animate-pulse space-y-6">
          <div className="h-8 w-48 rounded bg-gray-200"></div>
          <div className="h-12 w-40 rounded bg-gray-200"></div>
          <div className="h-6 w-32 rounded bg-gray-200"></div>
        </div>
      </div>
    )
  }

  const isPositiveChange = portfolio.dailyChange >= 0

  return (
    <div
      onClick={() => navigate(`/portfolio/${portfolio.id}`)}
      className="group cursor-pointer rounded-2xl bg-white p-8 shadow-lg transition-all hover:shadow-xl hover:scale-[1.02]"
      data-testid={`portfolio-card-${portfolio.id}`}
    >
      {/* Portfolio Name */}
      <h2 className="mb-6 text-2xl font-semibold text-gray-900">
        {portfolio.name}
      </h2>

      {/* Total Value - Prominent */}
      <div className="mb-6">
        <p className="mb-2 text-sm font-medium uppercase tracking-wide text-gray-500">
          Total Value
        </p>
        <p
          className="text-4xl font-bold text-gray-900"
          data-testid={`portfolio-card-value-${portfolio.id}`}
        >
          {formatCurrency(portfolio.totalValue)}
        </p>
      </div>

      {/* Divider */}
      <div className="mb-6 h-px bg-gray-200"></div>

      {/* Cash Balance and Daily Change - Side by Side */}
      <div className="grid grid-cols-2 gap-6">
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
            Cash Balance
          </p>
          <p className="text-xl font-semibold text-gray-900">
            {formatCurrency(portfolio.cashBalance)}
          </p>
        </div>
        <div>
          <p className="mb-2 text-xs font-medium uppercase tracking-wide text-gray-500">
            Daily Change
          </p>
          <div className="space-y-1">
            <p
              className={`text-xl font-semibold ${
                isPositiveChange ? 'text-positive' : 'text-negative'
              }`}
            >
              {isPositiveChange ? '+' : ''}
              {formatCurrency(portfolio.dailyChange)}
            </p>
            <p
              className={`text-sm font-medium ${
                isPositiveChange ? 'text-positive' : 'text-negative'
              }`}
            >
              {formatPercent(portfolio.dailyChangePercent / 100)}
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

/**
 * Dashboard Variant A: Modern Minimal
 *
 * Design characteristics:
 * - Apple-like minimalism
 * - Generous whitespace and padding
 * - Larger typography with clear hierarchy
 * - Elevated cards with subtle shadows
 * - Spacious grid (2 columns max)
 * - Calm, professional aesthetic
 */
export function DashboardVariantA(): React.JSX.Element {
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
      <div className="flex min-h-screen items-center justify-center bg-gray-50 px-6 py-12">
        <div className="rounded-2xl bg-white p-8 shadow-lg">
          <h2 className="mb-4 text-2xl font-semibold text-red-600">Error</h2>
          <p className="text-gray-700">
            {error instanceof Error
              ? error.message
              : 'Failed to load portfolios'}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-12">
      <div className="mx-auto max-w-7xl">
        {/* Header - Large and Spacious */}
        <header className="mb-12">
          <div className="mb-6">
            <h1 className="mb-4 text-5xl font-light text-gray-900">
              Your Portfolios
            </h1>
            <p className="text-xl text-gray-600">
              Track and manage your investments
            </p>
          </div>
          <button
            onClick={() => setShowCreateModal(true)}
            data-testid="create-portfolio-header-btn"
            className="rounded-xl bg-blue-600 px-8 py-4 text-lg font-semibold text-white shadow-md transition-all hover:bg-blue-700 hover:shadow-lg focus:outline-none focus:ring-4 focus:ring-blue-500/50"
          >
            Create New Portfolio
          </button>
        </header>

        {/* Portfolio Grid or Loading/Empty State */}
        {portfoliosLoading ? (
          <div className="grid gap-8 lg:grid-cols-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="rounded-2xl bg-white p-8 shadow-lg">
                <div className="animate-pulse space-y-6">
                  <div className="h-8 w-48 rounded bg-gray-200"></div>
                  <div className="h-12 w-40 rounded bg-gray-200"></div>
                  <div className="h-6 w-32 rounded bg-gray-200"></div>
                </div>
              </div>
            ))}
          </div>
        ) : !portfolios || portfolios.length === 0 ? (
          <div className="flex flex-col items-center justify-center rounded-2xl bg-white p-16 shadow-lg">
            <div className="mb-6 text-center">
              <h2 className="mb-3 text-3xl font-semibold text-gray-900">
                No Portfolios Yet
              </h2>
              <p className="text-lg text-gray-600">
                Create your first portfolio to start tracking your investments
              </p>
            </div>
            <button
              onClick={() => setShowCreateModal(true)}
              data-testid="create-first-portfolio-btn"
              className="rounded-xl bg-blue-600 px-12 py-4 text-lg font-semibold text-white shadow-md transition-all hover:bg-blue-700 hover:shadow-lg focus:outline-none focus:ring-4 focus:ring-blue-500/50"
            >
              Create Your First Portfolio
            </button>
          </div>
        ) : (
          <>
            {/* Portfolio Count */}
            <div className="mb-8">
              <p className="text-lg text-gray-600">
                {portfolios.length} portfolio
                {portfolios.length !== 1 ? 's' : ''}
              </p>
            </div>

            {/* Spacious Grid - 2 columns max */}
            <div
              className="grid gap-8 lg:grid-cols-2"
              data-testid="portfolio-grid"
            >
              {portfolios.map((portfolioDTO) => (
                <PortfolioCardModernMinimal
                  key={portfolioDTO.id}
                  portfolioDTO={portfolioDTO}
                />
              ))}
            </div>
          </>
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
