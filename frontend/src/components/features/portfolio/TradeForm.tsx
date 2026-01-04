import { useState, useMemo, useEffect } from 'react'
import type { TradeRequest } from '@/services/api/types'
import type { Holding } from '@/types/portfolio'

interface TradeFormProps {
  onSubmit: (trade: TradeRequest) => void
  isSubmitting?: boolean
  holdings?: Holding[]
  portfolioId?: string  // Reserved for future use (e.g., analytics)
  quickSellData?: { ticker: string; quantity: number } | null
}

export function TradeForm({
  onSubmit,
  isSubmitting = false,
  holdings = [],
  quickSellData,
}: TradeFormProps): React.JSX.Element {
  const [action, setAction] = useState<'BUY' | 'SELL'>('BUY')
  const [ticker, setTicker] = useState('')
  const [quantity, setQuantity] = useState('')
  const [price, setPrice] = useState('')

  // Handle quick sell data - use startTransition to avoid lint warning
  useEffect(() => {
    if (quickSellData) {
      // Use a microtask to batch the updates
      Promise.resolve().then(() => {
        setAction('SELL')
        setTicker(quickSellData.ticker)
        setQuantity(quickSellData.quantity.toString())
      })
    }
  }, [quickSellData])

  // Find holding for the current ticker when SELL is selected
  const currentHolding = useMemo(() => {
    if (action === 'SELL' && ticker.trim()) {
      return holdings.find(h => h.ticker.toUpperCase() === ticker.trim().toUpperCase())
    }
    return undefined
  }, [action, ticker, holdings])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()

    if (!ticker || !quantity) {
      return
    }

    const trade: TradeRequest = {
      action,
      ticker: ticker.trim().toUpperCase(),
      quantity: quantity,
    }

    onSubmit(trade)

    // Reset form
    setTicker('')
    setQuantity('')
    setPrice('')
  }

  const isValid =
    ticker.trim() !== '' &&
    quantity !== '' &&
    parseFloat(quantity) > 0 &&
    // For SELL: can only sell if holding exists
    (action === 'BUY' || currentHolding !== undefined)

  const estimatedTotal =
    isValid && price !== '' && parseFloat(price) > 0
      ? parseFloat(quantity) * parseFloat(price)
      : 0

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
              data-testid="trade-form-action-buy"
              onClick={() => setAction('BUY')}
              className={`flex-1 rounded-lg px-4 py-2 font-medium transition-colors ${
                action === 'BUY'
                  ? 'bg-blue-600 text-white hover:bg-blue-700'
                  : 'bg-gray-200 text-gray-700 hover:bg-gray-300 dark:bg-gray-700 dark:text-gray-300 dark:hover:bg-gray-600'
              }`}
              disabled={isSubmitting}
            >
              Buy
            </button>
            <button
              type="button"
              data-testid="trade-form-action-sell"
              onClick={() => setAction('SELL')}
              className={`flex-1 rounded-lg px-4 py-2 font-medium transition-colors ${
                action === 'SELL'
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
            data-testid="trade-form-ticker-input"
            type="text"
            value={ticker}
            onChange={(e) => setTicker(e.target.value)}
            placeholder="AAPL"
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400"
            disabled={isSubmitting}
            required
            maxLength={5}
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
            data-testid="trade-form-quantity-input"
            type="number"
            min="0.0001"
            step="0.0001"
            value={quantity}
            onChange={(e) => setQuantity(e.target.value)}
            placeholder="100"
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400"
            disabled={isSubmitting}
            required
          />
          {/* Show holdings info for SELL */}
          {action === 'SELL' && ticker.trim() !== '' && (
            <div className="mt-2" data-testid="trade-form-holdings-info">
              {currentHolding ? (
                <p className="text-sm text-gray-600 dark:text-gray-400">
                  You own{' '}
                  <span className="font-semibold text-gray-900 dark:text-white">
                    {currentHolding.quantity.toLocaleString('en-US', {
                      minimumFractionDigits: 0,
                      maximumFractionDigits: 4,
                    })}
                  </span>{' '}
                  shares of {ticker.toUpperCase()}
                </p>
              ) : (
                <p className="text-sm text-red-600 dark:text-red-400" data-testid="trade-form-no-holdings">
                  You don't own any shares of {ticker.toUpperCase()}
                </p>
              )}
            </div>
          )}
        </div>

        {/* Price Per Share Input (Optional - For Estimation Only) */}
        <div>
          <label
            htmlFor="price"
            className="mb-2 block text-sm font-medium text-gray-700 dark:text-gray-300"
          >
            Price Per Share ($) <span className="text-gray-500">(Optional - for estimation)</span>
          </label>
          <input
            id="price"
            data-testid="trade-form-price-input"
            type="number"
            min="0.01"
            step="0.01"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
            placeholder="150.00"
            className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400"
            disabled={isSubmitting}
          />
          <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
            Actual trade will execute at current market price
          </p>
        </div>

        {/* Preview */}
        {isValid && (
          <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-900">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {action === 'BUY' ? 'Buying' : 'Selling'} {quantity} shares of{' '}
              {ticker.toUpperCase()}
              {price !== '' && parseFloat(price) > 0 ? ` at ~$${price}` : ''}
            </p>
            {estimatedTotal > 0 && (
              <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
                Estimated Total: ${estimatedTotal.toFixed(2)}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              Trade will execute at current market price
            </p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          data-testid={action === 'BUY' ? 'trade-form-buy-button' : 'trade-form-sell-button'}
          disabled={!isValid || isSubmitting}
          className={`w-full rounded-lg px-4 py-3 font-semibold text-white transition-colors ${
            action === 'BUY'
              ? 'bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400'
              : 'bg-negative hover:bg-negative-dark disabled:bg-gray-400'
          } disabled:cursor-not-allowed`}
        >
          {isSubmitting
            ? 'Processing...'
            : action === 'BUY'
              ? 'Execute Buy Order'
              : 'Execute Sell Order'}
        </button>
      </form>
    </div>
  )
}
