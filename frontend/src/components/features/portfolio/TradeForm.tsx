import { useState } from 'react'
import type { TradeRequest } from '@/types/portfolio'

interface TradeFormProps {
  portfolioId: string
  onSubmit: (trade: TradeRequest) => void
  isSubmitting?: boolean
}

export function TradeForm({
  portfolioId,
  onSubmit,
  isSubmitting = false,
}: TradeFormProps): React.JSX.Element {
  const [action, setAction] = useState<'buy' | 'sell'>('buy')
  const [ticker, setTicker] = useState('')
  const [quantity, setQuantity] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!ticker || !quantity) {
      return
    }

    const trade: TradeRequest = {
      portfolioId,
      action,
      ticker: ticker.trim().toUpperCase(),
      quantity: parseInt(quantity, 10),
    }

    onSubmit(trade)

    // Reset form
    setTicker('')
    setQuantity('')
  }

  const isValid = ticker.trim() !== '' && quantity !== '' && parseInt(quantity, 10) > 0

  return (
    <div className="rounded-lg border border-gray-300 bg-white p-6 shadow-sm dark:border-gray-700 dark:bg-gray-800">
      <h3 className="mb-4 text-lg font-semibold text-gray-900 dark:text-white">
        Execute Trade
      </h3>

      <form onSubmit={handleSubmit} className="space-y-4">
        {/* Action Toggle */}
        <div>
          <label className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300">
            Action
          </label>
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setAction('buy')}
              className={`flex-1 rounded-lg px-4 py-2 font-medium transition-colors ${
                action === 'buy'
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
              disabled={isSubmitting}
            >
              Buy
            </button>
            <button
              type="button"
              onClick={() => setAction('sell')}
              className={`flex-1 rounded-lg px-4 py-2 font-medium transition-colors ${
                action === 'sell'
                  ? 'bg-negative text-white hover:bg-negative-dark'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
              disabled={isSubmitting}
            >
              Sell
            </button>
          </div>
        </div>

        {/* Symbol Input */}
        <div>
          <label
            htmlFor="ticker"
            className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Symbol
          </label>
          <input
            id="ticker"
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="AAPL"
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400"
            disabled={isSubmitting}
            required
          />
        </div>

        {/* Quantity Input */}
        <div>
          <label
            htmlFor="quantity"
            className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Quantity
          </label>
          <input
            id="quantity"
            type="number"
            min="1"
            step="1"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="100"
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400"
            disabled={isSubmitting}
            required
          />
        </div>

        {/* Preview (placeholder) */}
        {isValid && (
          <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-900">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {action === 'buy' ? 'Buying' : 'Selling'} {quantity} shares of{' '}
              {ticker.toUpperCase()}
            </p>
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-500">
              Estimated price will be calculated at execution
            </p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          disabled={!isValid || isSubmitting}
          className={`w-full rounded-lg px-4 py-3 font-semibold text-white transition-colors ${
            action === 'buy'
              ? 'bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400'
              : 'bg-negative hover:bg-negative-dark disabled:bg-gray-400'
          } disabled:cursor-not-allowed`}
        >
          {isSubmitting
            ? 'Processing...'
            : action === 'buy'
              ? 'Execute Buy Order'
              : 'Execute Sell Order'}
        </button>
      </form>
    </div>
  )
}
