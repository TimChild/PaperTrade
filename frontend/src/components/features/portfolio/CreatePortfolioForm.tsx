/**
 * Editorial portfolio creation form. Used inside the Dialog.
 */
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useCreatePortfolio } from '@/hooks/usePortfolio'
import { toasts } from '@/utils/toast'
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

  const handleSubmit = async (e: React.FormEvent): Promise<void> => {
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
        navigate(`/portfolio/${result.portfolio_id}`)
      }

      toasts.portfolioCreated(name.trim())
    } catch (err) {
      setError(
        err instanceof Error ? err.message : 'Failed to create portfolio'
      )
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      {/* Portfolio Name */}
      <div className="space-y-1.5">
        <Label htmlFor="portfolio-name">
          Portfolio name <span className="text-loss">*</span>
        </Label>
        <Input
          id="portfolio-name"
          data-testid="create-portfolio-name-input"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
          maxLength={100}
          placeholder="My investment portfolio"
          aria-describedby="portfolio-name-help"
        />
        <p id="portfolio-name-help" className="text-body-sm text-ink-subtle">
          Give your portfolio a descriptive name (1–100 characters).
        </p>
      </div>

      {/* Initial Deposit */}
      <div className="space-y-1.5">
        <Label htmlFor="initial-deposit">Initial deposit (USD)</Label>
        <div className="flex items-center gap-2">
          <span className="text-ink-muted font-tabular text-body-sm">$</span>
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
        <p id="initial-deposit-help" className="text-body-sm text-ink-subtle">
          Start with an initial cash balance (must be greater than $0.00).
        </p>
      </div>

      {/* Error Message */}
      {error && (
        <div
          className="rounded-editorial border border-hairline bg-loss-soft/40 p-3 text-body-sm text-ink"
          role="alert"
        >
          {error}
        </div>
      )}

      {/* API Error (from mutation) */}
      {createPortfolio.isError && (
        <div
          className="rounded-editorial border border-hairline bg-loss-soft/40 p-3 text-body-sm text-ink"
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
            variant="ghost"
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
          {createPortfolio.isPending ? 'Creating...' : 'Create portfolio'}
        </Button>
      </div>
    </form>
  )
}
