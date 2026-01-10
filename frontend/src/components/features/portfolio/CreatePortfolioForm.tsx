/**
 * Portfolio creation form component
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreatePortfolio } from '@/hooks/usePortfolio'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'

interface CreatePortfolioFormProps {
  onSuccess?: (portfolioId: string) => void
  onCancel?: () => void
}

export function CreatePortfolioForm({
  onSuccess,
  onCancel,
}: CreatePortfolioFormProps): React.JSX.Element {
  const [name, setName] = useState('')
  const [initialDeposit, setInitialDeposit] = useState('1000.00')
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
    if (isNaN(depositAmount) || depositAmount <= 0) {
      setError('Initial deposit must be a positive number greater than zero')
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
      setError(
        err instanceof Error ? err.message : 'Failed to create portfolio'
      )
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Portfolio Name */}
      <div>
        <Label htmlFor="portfolio-name">
          Portfolio Name <span className="text-negative">*</span>
        </Label>
        <Input
          id="portfolio-name"
          data-testid="create-portfolio-name-input"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={100}
          placeholder="My Investment Portfolio"
          aria-describedby="portfolio-name-help"
        />
        <p
          id="portfolio-name-help"
          className="mt-1 text-xs text-foreground-tertiary"
        >
          Give your portfolio a descriptive name (1-100 characters)
        </p>
      </div>

      {/* Initial Deposit */}
      <div>
        <Label htmlFor="initial-deposit">Initial Deposit (USD)</Label>
        <div className="mt-1 flex items-center">
          <span className="mr-2 text-foreground-secondary">$</span>
          <Input
            id="initial-deposit"
            data-testid="create-portfolio-deposit-input"
            type="number"
            step="0.01"
            value={initialDeposit}
            onChange={(e) => setInitialDeposit(e.target.value)}
            placeholder="0.00"
            aria-describedby="initial-deposit-help"
          />
        </div>
        <p
          id="initial-deposit-help"
          className="mt-1 text-xs text-foreground-tertiary"
        >
          Start with an initial cash balance (must be greater than $0.00)
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
          <Button
            type="button"
            variant="outline"
            data-testid="create-portfolio-cancel-button"
            onClick={onCancel}
            className="flex-1"
          >
            Cancel
          </Button>
        )}
        <Button
          type="submit"
          data-testid="submit-portfolio-form-btn"
          disabled={createPortfolio.isPending}
          className="flex-1"
        >
          {createPortfolio.isPending ? 'Creating...' : 'Create Portfolio'}
        </Button>
      </div>
    </form>
  )
}
