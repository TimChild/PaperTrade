import { useState, useMemo, useEffect } from 'react'
import type { TradeRequest } from '@/services/api/types'
import type { Holding } from '@/types/portfolio'
import { useDebounce } from '@/hooks/useDebounce'
import { usePriceQuery } from '@/hooks/usePriceQuery'

interface TradeFormProps {
  onSubmit: (trade: TradeRequest) => void
  isSubmitting?: boolean
  holdings?: Holding[]
  portfolioId?: string // Reserved for future use (e.g., analytics)
  initialAction?: 'BUY' | 'SELL'
  initialTicker?: string
  initialQuantity?: string
}

export function TradeForm({
  onSubmit,
  isSubmitting = false,
  holdings = [],
  initialAction = 'BUY',
  initialTicker = '',
  initialQuantity = '',
}: TradeFormProps): React.JSX.Element {
  const [action, setAction] = useState<'BUY' | 'SELL'>(initialAction)
  const [ticker, setTicker] = useState(initialTicker)
  const [quantity, setQuantity] = useState(initialQuantity)
  const [price, setPrice] = useState('')
  const [isPriceManuallySet, setIsPriceManuallySet] = useState(false)
  const [backtestMode, setBacktestMode] = useState(false)
  const [backtestDate, setBacktestDate] = useState('')

  // Debounce ticker input to avoid excessive API calls
  const debouncedTicker = useDebounce(ticker.trim().toUpperCase(), 500)

  // Fetch current price for the debounced ticker (only when not in backtest mode)
  const {
    data: priceData,
    isLoading: isPriceLoading,
    error: priceError,
  } = usePriceQuery(debouncedTicker)

  // Auto-populate price field when price data is fetched
  // Only auto-populate if not in backtest mode and price hasn't been manually set
  /* eslint-disable react-hooks/set-state-in-effect */
  useEffect(() => {
    if (priceData && !backtestMode && debouncedTicker && !isPriceManuallySet) {
      setPrice(priceData.price.amount.toString())
    }
  }, [priceData, backtestMode, debouncedTicker, isPriceManuallySet])

  // Reset manual price flag when ticker changes
  useEffect(() => {
    setIsPriceManuallySet(false)
  }, [debouncedTicker])
  /* eslint-enable react-hooks/set-state-in-effect */

  // Handle manual price changes
  const handlePriceChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setPrice(e.target.value)
    setIsPriceManuallySet(true)
  }

  // Find holding for the current ticker when SELL is selected
  const currentHolding = useMemo(() => {
    if (action === 'SELL' && ticker.trim()) {
      return holdings.find(
        (h) => h.ticker.toUpperCase() === ticker.trim().toUpperCase()
      )
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

    // Add as_of if in backtest mode
    if (backtestMode && backtestDate) {
      trade.as_of = new Date(backtestDate).toISOString()
    }

    onSubmit(trade)

    // Reset form (keep backtest mode settings)
    setTicker('')
    setQuantity('')
    setPrice('')
    setIsPriceManuallySet(false)
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
                <p
                  className="text-sm text-red-600 dark:text-red-400"
                  data-testid="trade-form-no-holdings"
                >
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
            Price Per Share ($){' '}
            <span className="text-gray-500">(Optional - for estimation)</span>
          </label>
          <div className="relative">
            <input
              id="price"
              data-testid="trade-form-price-input"
              type="number"
              min="0.01"
              step="0.01"
              value={price}
              onChange={handlePriceChange}
              placeholder="150.00"
              className="w-full rounded-lg border border-gray-300 bg-white px-4 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400"
              disabled={isSubmitting}
            />
            {/* Loading spinner */}
            {isPriceLoading && debouncedTicker && !backtestMode && (
              <div
                className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
                data-testid="trade-form-price-loading"
              >
                <svg
                  className="h-5 w-5 animate-spin text-blue-500"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
              </div>
            )}
            {/* Success checkmark */}
            {priceData &&
              !isPriceLoading &&
              debouncedTicker &&
              !backtestMode && (
                <div
                  className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
                  data-testid="trade-form-price-success"
                >
                  <svg
                    className="h-5 w-5 text-green-500"
                    xmlns="http://www.w3.org/2000/svg"
                    viewBox="0 0 20 20"
                    fill="currentColor"
                  >
                    <path
                      fillRule="evenodd"
                      d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z"
                      clipRule="evenodd"
                    />
                  </svg>
                </div>
              )}
          </div>
          {/* Error message for invalid ticker */}
          {priceError && debouncedTicker && !backtestMode && (
            <p
              className="mt-1 text-xs text-red-600 dark:text-red-400"
              data-testid="trade-form-price-error"
            >
              Unable to fetch price for {debouncedTicker}
            </p>
          )}
          {/* Info message */}
          {!priceError && (
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {backtestMode && backtestDate
                ? 'Trade will execute with historical price from selected date'
                : debouncedTicker && isPriceLoading
                  ? 'Fetching current price...'
                  : debouncedTicker && priceData
                    ? `Current price auto-populated (as of ${new Date(priceData.timestamp).toLocaleTimeString()})`
                    : 'Actual trade will execute at current market price'}
            </p>
          )}
        </div>

        {/* Backtest Mode Section */}
        <div className="rounded-lg border border-amber-300 bg-amber-50 p-4 dark:border-amber-700 dark:bg-amber-950">
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              data-testid="backtest-mode-toggle"
              checked={backtestMode}
              onChange={(e) => setBacktestMode(e.target.checked)}
              disabled={isSubmitting}
              className="h-4 w-4 rounded border-gray-300 bg-gray-100 text-blue-600 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:ring-offset-gray-800 dark:focus:ring-blue-600"
            />
            <span className="font-medium text-gray-900 dark:text-white">
              Backtest Mode
            </span>
          </label>
          <p className="mt-1 text-xs text-gray-600 dark:text-gray-400">
            Execute trade with historical prices for strategy testing
          </p>

          {backtestMode && (
            <div className="mt-3">
              <label
                htmlFor="backtest-date"
                className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300"
              >
                Trade Date
              </label>
              <input
                id="backtest-date"
                type="date"
                data-testid="backtest-date-picker"
                className="w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-gray-900 focus:border-blue-500 focus:ring-2 focus:ring-blue-500 dark:border-gray-600 dark:bg-gray-700 dark:text-white dark:focus:border-blue-400 dark:focus:ring-blue-400"
                max={new Date().toISOString().split('T')[0]}
                value={backtestDate}
                onChange={(e) => setBacktestDate(e.target.value)}
                disabled={isSubmitting}
              />

              {/* Warning indicator */}
              <div className="mt-2 flex items-center gap-1 text-amber-700 dark:text-amber-400">
                <svg
                  className="h-4 w-4"
                  fill="currentColor"
                  viewBox="0 0 20 20"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    fillRule="evenodd"
                    d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z"
                    clipRule="evenodd"
                  />
                </svg>
                <span className="text-sm" data-testid="backtest-mode-warning">
                  Trade will use historical prices
                </span>
              </div>
            </div>
          )}
        </div>

        {/* Preview */}
        {isValid && (
          <div className="rounded-lg bg-gray-50 p-4 dark:bg-gray-900">
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {action === 'BUY' ? 'Buying' : 'Selling'} {quantity} shares of{' '}
              {ticker.toUpperCase()}
              {price !== '' && parseFloat(price) > 0 ? ` at ~$${price}` : ''}
              {backtestMode && backtestDate && (
                <span className="ml-2 text-amber-600 dark:text-amber-400">
                  (Backtest: {new Date(backtestDate).toLocaleDateString()})
                </span>
              )}
            </p>
            {estimatedTotal > 0 && (
              <p className="mt-1 text-sm font-semibold text-gray-900 dark:text-white">
                Estimated Total: ${estimatedTotal.toFixed(2)}
              </p>
            )}
            <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
              {backtestMode && backtestDate
                ? 'Trade will execute with historical price from selected date'
                : 'Trade will execute at current market price'}
            </p>
          </div>
        )}

        {/* Submit Button */}
        <button
          type="submit"
          data-testid={
            action === 'BUY'
              ? 'trade-form-buy-button'
              : 'trade-form-sell-button'
          }
          disabled={!isValid || isSubmitting}
          className={`w-full rounded-lg px-4 py-3 font-semibold text-white transition-colors ${
            action === 'BUY'
              ? 'bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400'
              : 'bg-negative hover:bg-negative-dark disabled:bg-gray-400'
          } disabled:cursor-not-allowed`}
        >
          {isSubmitting
            ? 'Processing...'
            : backtestMode
              ? `Execute Backtest ${action === 'BUY' ? 'Buy' : 'Sell'} Order`
              : action === 'BUY'
                ? 'Execute Buy Order'
                : 'Execute Sell Order'}
        </button>
      </form>
    </div>
  )
}
