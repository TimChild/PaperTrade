/**
 * Form for creating a new trading strategy
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useCreateStrategy } from '@/hooks/useStrategies'
import type { StrategyType } from '@/services/api/types'
import toast from 'react-hot-toast'

interface CreateStrategyFormProps {
  onSuccess: () => void
  onCancel: () => void
}

const STRATEGY_TYPE_OPTIONS: { value: StrategyType; label: string }[] = [
  { value: 'BUY_AND_HOLD', label: 'Buy & Hold' },
  { value: 'DOLLAR_COST_AVERAGING', label: 'Dollar Cost Averaging' },
  { value: 'MOVING_AVERAGE_CROSSOVER', label: 'Moving Average Crossover' },
]

export function CreateStrategyForm({
  onSuccess,
  onCancel,
}: CreateStrategyFormProps): React.JSX.Element {
  const [name, setName] = useState('')
  const [strategyType, setStrategyType] = useState<StrategyType>('BUY_AND_HOLD')
  const [tickersInput, setTickersInput] = useState('')

  // BUY_AND_HOLD / DCA allocation per ticker (ticker -> fraction string)
  const [allocations, setAllocations] = useState<Record<string, string>>({})

  // DCA-specific
  const [frequencyDays, setFrequencyDays] = useState('30')
  const [amountPerPeriod, setAmountPerPeriod] = useState('100')

  // Moving Average Crossover-specific
  const [fastWindow, setFastWindow] = useState('10')
  const [slowWindow, setSlowWindow] = useState('50')
  const [investFraction, setInvestFraction] = useState('0.9')

  const [errors, setErrors] = useState<Record<string, string>>({})

  const createStrategy = useCreateStrategy()

  const tickers = tickersInput
    .split(',')
    .map((t) => t.trim().toUpperCase())
    .filter(Boolean)

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!name.trim()) {
      newErrors.name = 'Strategy name is required'
    }

    if (tickers.length === 0) {
      newErrors.tickers = 'At least one ticker is required'
    }

    if (
      strategyType === 'BUY_AND_HOLD' ||
      strategyType === 'DOLLAR_COST_AVERAGING'
    ) {
      const total = tickers.reduce((sum, ticker) => {
        const val = parseFloat(allocations[ticker] ?? '0')
        return sum + (Number.isFinite(val) ? val : 0)
      }, 0)
      if (tickers.length > 0 && Math.abs(total - 1.0) > 0.01) {
        newErrors.allocations = `Allocations must sum to 1.0 (currently ${total.toFixed(2)})`
      }
    }

    if (strategyType === 'DOLLAR_COST_AVERAGING') {
      const freq = parseInt(frequencyDays, 10)
      if (!Number.isInteger(freq) || freq < 1) {
        newErrors.frequencyDays = 'Frequency must be a positive integer'
      }
      const amount = parseFloat(amountPerPeriod)
      if (!Number.isFinite(amount) || amount <= 0) {
        newErrors.amountPerPeriod = 'Amount must be a positive number'
      }
    }

    if (strategyType === 'MOVING_AVERAGE_CROSSOVER') {
      const fast = parseInt(fastWindow, 10)
      const slow = parseInt(slowWindow, 10)
      const frac = parseFloat(investFraction)

      if (!Number.isInteger(fast) || fast < 2 || fast > 200) {
        newErrors.fastWindow =
          'Fast window must be an integer between 2 and 200'
      }
      if (!Number.isInteger(slow) || slow <= fast) {
        newErrors.slowWindow = 'Slow window must be greater than fast window'
      }
      if (!Number.isFinite(frac) || frac <= 0 || frac > 1) {
        newErrors.investFraction = 'Invest fraction must be between 0 and 1'
      }
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const buildParameters = (): Record<string, unknown> => {
    if (strategyType === 'BUY_AND_HOLD') {
      const alloc: Record<string, number> = {}
      tickers.forEach((t) => {
        alloc[t] = parseFloat(allocations[t] ?? '0')
      })
      return { allocation: alloc }
    }

    if (strategyType === 'DOLLAR_COST_AVERAGING') {
      const alloc: Record<string, number> = {}
      tickers.forEach((t) => {
        alloc[t] = parseFloat(allocations[t] ?? '0')
      })
      return {
        frequency_days: parseInt(frequencyDays, 10),
        amount_per_period: parseFloat(amountPerPeriod),
        allocation: alloc,
      }
    }

    // MOVING_AVERAGE_CROSSOVER
    return {
      fast_window: parseInt(fastWindow, 10),
      slow_window: parseInt(slowWindow, 10),
      invest_fraction: parseFloat(investFraction),
    }
  }

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!validate()) return

    createStrategy.mutate(
      {
        name: name.trim(),
        strategy_type: strategyType,
        tickers,
        parameters: buildParameters(),
      },
      {
        onSuccess: () => {
          toast.success('Strategy created')
          onSuccess()
        },
        onError: () => {
          toast.error('Failed to create strategy')
        },
      }
    )
  }

  const handleAllocationChange = (ticker: string, value: string) => {
    setAllocations((prev) => ({ ...prev, [ticker]: value }))
  }

  const allocationTotal = tickers.reduce((sum, ticker) => {
    const val = parseFloat(allocations[ticker] ?? '0')
    return sum + (Number.isFinite(val) ? val : 0)
  }, 0)

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create Strategy</CardTitle>
      </CardHeader>
      <CardContent>
        <form
          onSubmit={handleSubmit}
          data-testid="create-strategy-form"
          className="space-y-4"
        >
          {/* Name */}
          <div className="space-y-1">
            <Label htmlFor="strategy-name">Strategy Name</Label>
            <Input
              id="strategy-name"
              data-testid="strategy-name-input"
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="My Strategy"
            />
            {errors.name && (
              <p className="text-sm text-red-600 dark:text-red-400">
                {errors.name}
              </p>
            )}
          </div>

          {/* Strategy type */}
          <div className="space-y-1">
            <Label htmlFor="strategy-type">Strategy Type</Label>
            <select
              id="strategy-type"
              data-testid="strategy-type-select"
              value={strategyType}
              onChange={(e) => setStrategyType(e.target.value as StrategyType)}
              className="flex h-10 w-full rounded-input border border-gray-300 bg-white px-3 py-2 text-sm text-foreground-primary focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary disabled:cursor-not-allowed disabled:opacity-50 dark:border-gray-700 dark:bg-gray-900"
            >
              {STRATEGY_TYPE_OPTIONS.map(({ value, label }) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Tickers */}
          <div className="space-y-1">
            <Label htmlFor="strategy-tickers">
              Tickers{' '}
              <span className="text-xs text-gray-500">(comma-separated)</span>
            </Label>
            <Input
              id="strategy-tickers"
              data-testid="strategy-tickers-input"
              value={tickersInput}
              onChange={(e) => setTickersInput(e.target.value)}
              placeholder="AAPL, MSFT, GOOG"
            />
            {errors.tickers && (
              <p className="text-sm text-red-600 dark:text-red-400">
                {errors.tickers}
              </p>
            )}
            {tickers.length > 0 && (
              <div className="mt-1 flex flex-wrap gap-1">
                {tickers.map((t) => (
                  <span
                    key={t}
                    className="rounded bg-gray-100 px-2 py-0.5 font-mono text-xs dark:bg-gray-700 dark:text-gray-200"
                  >
                    {t}
                  </span>
                ))}
              </div>
            )}
          </div>

          {/* Parameters: allocation-based strategies */}
          {(strategyType === 'BUY_AND_HOLD' ||
            strategyType === 'DOLLAR_COST_AVERAGING') &&
            tickers.length > 0 && (
              <div className="space-y-2">
                <Label>
                  Allocation per Ticker{' '}
                  <span className="text-xs text-gray-500">
                    (must sum to 1.0)
                  </span>
                </Label>
                {tickers.map((ticker) => (
                  <div key={ticker} className="flex items-center gap-2">
                    <span className="w-20 font-mono text-sm">{ticker}</span>
                    <Input
                      type="number"
                      step="0.01"
                      min="0"
                      max="1"
                      data-testid={`allocation-${ticker}`}
                      value={allocations[ticker] ?? ''}
                      onChange={(e) =>
                        handleAllocationChange(ticker, e.target.value)
                      }
                      placeholder="0.50"
                      className="w-28"
                    />
                  </div>
                ))}
                <p
                  className={`text-xs ${Math.abs(allocationTotal - 1.0) < 0.01 ? 'text-green-600 dark:text-green-400' : 'text-gray-500'}`}
                >
                  Total: {allocationTotal.toFixed(2)}
                </p>
                {errors.allocations && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {errors.allocations}
                  </p>
                )}
              </div>
            )}

          {/* Parameters: DCA-specific */}
          {strategyType === 'DOLLAR_COST_AVERAGING' && (
            <>
              <div className="space-y-1">
                <Label htmlFor="frequency-days">Frequency (days)</Label>
                <Input
                  id="frequency-days"
                  data-testid="frequency-days-input"
                  type="number"
                  min="1"
                  value={frequencyDays}
                  onChange={(e) => setFrequencyDays(e.target.value)}
                  placeholder="30"
                />
                {errors.frequencyDays && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {errors.frequencyDays}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="amount-per-period">Amount per Period ($)</Label>
                <Input
                  id="amount-per-period"
                  data-testid="amount-per-period-input"
                  type="number"
                  min="0.01"
                  step="0.01"
                  value={amountPerPeriod}
                  onChange={(e) => setAmountPerPeriod(e.target.value)}
                  placeholder="100"
                />
                {errors.amountPerPeriod && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {errors.amountPerPeriod}
                  </p>
                )}
              </div>
            </>
          )}

          {/* Parameters: Moving Average Crossover */}
          {strategyType === 'MOVING_AVERAGE_CROSSOVER' && (
            <>
              <div className="space-y-1">
                <Label htmlFor="fast-window">Fast Window (2–200)</Label>
                <Input
                  id="fast-window"
                  data-testid="fast-window-input"
                  type="number"
                  min="2"
                  max="200"
                  value={fastWindow}
                  onChange={(e) => setFastWindow(e.target.value)}
                  placeholder="10"
                />
                {errors.fastWindow && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {errors.fastWindow}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="slow-window">
                  Slow Window (must be &gt; fast)
                </Label>
                <Input
                  id="slow-window"
                  data-testid="slow-window-input"
                  type="number"
                  min="3"
                  max="500"
                  value={slowWindow}
                  onChange={(e) => setSlowWindow(e.target.value)}
                  placeholder="50"
                />
                {errors.slowWindow && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {errors.slowWindow}
                  </p>
                )}
              </div>
              <div className="space-y-1">
                <Label htmlFor="invest-fraction">Invest Fraction (0–1)</Label>
                <Input
                  id="invest-fraction"
                  data-testid="invest-fraction-input"
                  type="number"
                  min="0.01"
                  max="1"
                  step="0.01"
                  value={investFraction}
                  onChange={(e) => setInvestFraction(e.target.value)}
                  placeholder="0.9"
                />
                {errors.investFraction && (
                  <p className="text-sm text-red-600 dark:text-red-400">
                    {errors.investFraction}
                  </p>
                )}
              </div>
            </>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="secondary"
              onClick={onCancel}
              data-testid="create-strategy-cancel"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              data-testid="create-strategy-submit"
              disabled={createStrategy.isPending}
            >
              {createStrategy.isPending ? 'Creating...' : 'Create Strategy'}
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}
