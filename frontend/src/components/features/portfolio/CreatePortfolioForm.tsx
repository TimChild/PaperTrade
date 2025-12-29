/**
 * Portfolio creation form component
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreatePortfolio } from '@/hooks/usePortfolio'

interface CreatePortfolioFormProps {
  onSuccess?: (portfolioId: string) => void
  onCancel?: () => void
}

export function CreatePortfolioForm({
  onSuccess,
  onCancel,
}: CreatePortfolioFormProps): React.JSX.Element {
  const [name, setName] = useState('')
  const [initialDeposit, setInitialDeposit] = useState('0.00')
  const [error, setError] = useState<string | null>(null)

  const createPortfolio = useCreatePortfolio()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    // Validate name
    if (!name.trim()) {
      setError('Portfolio name is required')
      return
    }

    if (name.length > 100) {
      setError('Portfolio name must be 100 characters or less')
      return
    }

    // Validate initial deposit
    const depositAmount = parseFloat(initialDeposit)
    if (isNaN(depositAmount) || depositAmount < 0) {
      setError('Initial deposit must be a positive number')
      return
    }

    try {
      const result = await createPortfolio.mutateAsync({
        name: name.trim(),
        initial_deposit: depositAmount.toFixed(2),
        currency: 'USD',
      })

      if (onSuccess) {
        onSuccess(result.portfolio_id)
      } else {
        // Navigate to the new portfolio by default
        navigate(`/portfolio/${result.portfolio_id}`)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create portfolio')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Portfolio Name */}
      <div>
        <label
          htmlFor="portfolio-name"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Portfolio Name <span className="text-red-500">*</span>
        </label>
        <input
          id="portfolio-name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={100}
          placeholder="My Investment Portfolio"
          className="mt-1 block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
          aria-describedby="portfolio-name-help"
        />
        <p id="portfolio-name-help" className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Give your portfolio a descriptive name (1-100 characters)
        </p>
      </div>

      {/* Initial Deposit */}
      <div>
        <label
          htmlFor="initial-deposit"
          className="block text-sm font-medium text-gray-700 dark:text-gray-300"
        >
          Initial Deposit (USD)
        </label>
        <div className="mt-1 flex items-center">
          <span className="mr-2 text-gray-600 dark:text-gray-400">$</span>
          <input
            id="initial-deposit"
            type="number"
            step="0.01"
            min="0"
            value={initialDeposit}
            onChange={(e) => setInitialDeposit(e.target.value)}
            placeholder="0.00"
            className="block w-full rounded-md border border-gray-300 px-3 py-2 shadow-sm focus:border-blue-500 focus:outline-none focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white"
            aria-describedby="initial-deposit-help"
          />
        </div>
        <p id="initial-deposit-help" className="mt-1 text-xs text-gray-500 dark:text-gray-400">
          Optional: Start with an initial cash balance (default: $0.00)
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div
          className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900 dark:text-red-200"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* API Error (from mutation) */}
      {createPortfolio.isError && (
        <div
          className="rounded-md bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900 dark:text-red-200"
          role="alert"
        >
          {createPortfolio.error instanceof Error
            ? createPortfolio.error.message
            : 'An error occurred while creating the portfolio'}
        </div>
      )}

      {/* Action Buttons */}
      <div className="flex gap-3 pt-2">
        {onCancel && (
          <button
            type="button"
            onClick={onCancel}
            className="flex-1 rounded-md border border-gray-300 bg-white px-4 py-2 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 dark:border-gray-600 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600"
          >
            Cancel
          </button>
        )}
        <button
          type="submit"
          disabled={createPortfolio.isPending || !name.trim()}
          className="flex-1 rounded-md bg-blue-600 px-4 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {createPortfolio.isPending ? 'Creating...' : 'Create Portfolio'}
        </button>
      </div>
    </form>
  )
}
