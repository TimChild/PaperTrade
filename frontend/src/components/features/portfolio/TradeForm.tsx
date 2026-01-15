import { useState, useMemo } from 'react'
import type { TradeRequest } from '@/services/api/types'
import type { Holding } from '@/types/portfolio'
import { useDebounce } from '@/hooks/useDebounce'
import { usePriceQuery } from '@/hooks/usePriceQuery'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'

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
  const [backtestMode, setBacktestMode] = useState(false)
  const [backtestDate, setBacktestDate] = useState('')

  // Debounce ticker input to avoid excessive API calls
  const debouncedTicker = useDebounce(ticker.trim().toUpperCase(), 500)

  // Fetch current price for the debounced ticker (only when not in backtest mode)
  const {
    data: priceData,
    isLoading: isPriceLoading,
    error: priceError,
  } = usePriceQuery(backtestMode ? '' : debouncedTicker)

  // Derive display price directly from priceData
  const displayPrice = priceData?.price?.amount?.toFixed(2) ?? '--'

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
    // Price derives from priceData - no state to reset
  }

  const isValid =
    ticker.trim() !== '' &&
    quantity !== '' &&
    parseFloat(quantity) > 0 &&
    // For SELL: can only sell if holding exists
    (action === 'BUY' || currentHolding !== undefined)

  const estimatedTotal =
    isValid && priceData?.price?.amount
      ? parseFloat(quantity) * priceData.price.amount
      : 0

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-heading-md">Execute Trade</CardTitle>
      </CardHeader>

      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {/* Action Toggle */}
          <div>
            <Label className="mb-2">Action</Label>
            <div className="flex gap-2">
              <Button
                type="button"
                data-testid="trade-form-action-buy"
                onClick={() => setAction('BUY')}
                variant={action === 'BUY' ? 'default' : 'secondary'}
                className="flex-1"
                disabled={isSubmitting}
              >
                Buy
              </Button>
              <Button
                type="button"
                data-testid="trade-form-action-sell"
                onClick={() => setAction('SELL')}
                variant={action === 'SELL' ? 'destructive' : 'secondary'}
                className="flex-1"
                disabled={isSubmitting}
              >
                Sell
              </Button>
            </div>
          </div>

          {/* Symbol Input */}
          <div>
            <Label htmlFor="ticker">Symbol</Label>
            <Input
              id="ticker"
              data-testid="trade-form-ticker-input"
              type="text"
              value={ticker}
              onChange={(e) => setTicker(e.target.value)}
              placeholder="AAPL"
              disabled={isSubmitting}
              required
              maxLength={5}
            />
          </div>

          {/* Quantity Input */}
          <div>
            <Label htmlFor="quantity">Quantity</Label>
            <Input
              id="quantity"
              data-testid="trade-form-quantity-input"
              type="number"
              min="0.0001"
              step="0.0001"
              value={quantity}
              onChange={(e) => setQuantity(e.target.value)}
              placeholder="100"
              disabled={isSubmitting}
              required
            />
            {/* Show holdings info for SELL */}
            {action === 'SELL' && ticker.trim() !== '' && (
              <div className="mt-2" data-testid="trade-form-holdings-info">
                {currentHolding ? (
                  <p className="text-sm text-foreground-secondary">
                    You own{' '}
                    <span className="font-semibold text-foreground-primary">
                      {currentHolding.quantity.toLocaleString('en-US', {
                        minimumFractionDigits: 0,
                        maximumFractionDigits: 4,
                      })}
                    </span>{' '}
                    shares of {ticker.toUpperCase()}
                  </p>
                ) : (
                  <p
                    className="text-sm text-negative"
                    data-testid="trade-form-no-holdings"
                  >
                    You don't own any shares of {ticker.toUpperCase()}
                  </p>
                )}
              </div>
            )}
          </div>

          {/* Price Display (Read-Only) */}
          <div>
            <Label htmlFor="price">Estimated Execution Price</Label>
            <div className="relative">
              <Input
                id="price"
                data-testid="trade-form-price-input"
                type="text"
                value={displayPrice}
                readOnly
                className="cursor-not-allowed bg-gray-50 dark:bg-gray-900"
              />
              {/* Loading spinner */}
              {isPriceLoading && debouncedTicker && !backtestMode && (
                <div
                  className="pointer-events-none absolute inset-y-0 right-0 flex items-center pr-3"
                  data-testid="trade-form-price-loading"
                >
                  <svg
                    className="h-5 w-5 animate-spin text-primary"
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
                      className="h-5 w-5 text-positive"
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
                className="mt-1 text-xs text-negative"
                data-testid="trade-form-price-error"
              >
                Unable to fetch price for {debouncedTicker}
              </p>
            )}
            {/* Info message */}
            {!priceError && (
              <p className="mt-1 text-xs text-foreground-tertiary">
                {backtestMode && backtestDate
                  ? 'Trade will execute with historical price from selected date'
                  : debouncedTicker && isPriceLoading
                    ? 'Fetching current price...'
                    : debouncedTicker && priceData
                      ? `Live market price (as of ${new Date(priceData.timestamp).toLocaleTimeString()})`
                      : 'Enter a ticker symbol to see current price'}
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
                className="h-4 w-4 rounded border-gray-300 bg-gray-100 text-primary focus:ring-2 focus:ring-primary dark:border-gray-600 dark:bg-gray-700 dark:ring-offset-gray-800"
              />
              <span className="font-medium text-foreground-primary">
                Backtest Mode
              </span>
            </label>
            <p className="mt-1 text-xs text-foreground-secondary">
              Execute trade with historical prices for strategy testing
            </p>

            {backtestMode && (
              <div className="mt-3">
                <Label htmlFor="backtest-date">Trade Date</Label>
                <Input
                  id="backtest-date"
                  type="date"
                  data-testid="backtest-date-picker"
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
              <p className="text-sm text-foreground-secondary">
                {action === 'BUY' ? 'Buying' : 'Selling'} {quantity} shares of{' '}
                {ticker.toUpperCase()}
                {priceData?.price?.amount
                  ? ` at ~$${priceData.price.amount.toFixed(2)}`
                  : ''}
                {backtestMode && backtestDate && (
                  <span className="ml-2 text-amber-600 dark:text-amber-400">
                    (Backtest: {new Date(backtestDate).toLocaleDateString()})
                  </span>
                )}
              </p>
              {estimatedTotal > 0 && (
                <p className="mt-1 text-sm font-semibold text-foreground-primary">
                  Estimated Total: ${estimatedTotal.toFixed(2)}
                </p>
              )}
              <p className="mt-1 text-xs text-foreground-tertiary">
                {backtestMode && backtestDate
                  ? 'Trade will execute with historical price from selected date'
                  : 'Trade will execute at current market price'}
              </p>
            </div>
          )}

          {/* Submit Button */}
          <Button
            type="submit"
            data-testid={
              action === 'BUY'
                ? 'trade-form-buy-button'
                : 'trade-form-sell-button'
            }
            disabled={!isValid || isSubmitting}
            variant={action === 'BUY' ? 'default' : 'destructive'}
            className="w-full"
          >
            {isSubmitting
              ? 'Processing...'
              : backtestMode
                ? `Execute Backtest ${action === 'BUY' ? 'Buy' : 'Sell'} Order`
                : action === 'BUY'
                  ? 'Execute Buy Order'
                  : 'Execute Sell Order'}
          </Button>
        </form>
      </CardContent>
    </Card>
  )
}
