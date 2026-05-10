/**
 * Editorial form for running a backtest. Lives in a flush Panel inside
 * the Backtests page.
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Panel } from '@/components/ui/Panel'
import { Eyebrow } from '@/components/ui/Eyebrow'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { useRunBacktest } from '@/hooks/useBacktests'
import { useStrategies } from '@/hooks/useStrategies'
import toast from 'react-hot-toast'

interface RunBacktestFormProps {
  onSuccess: () => void
  onCancel: () => void
}

const SELECT_CLASSES =
  'flex h-10 w-full rounded-input border border-hairline bg-canvas-raised/40 px-3 py-2 text-body-sm text-ink focus-visible:outline-none focus-visible:border-amber focus-visible:ring-1 focus-visible:ring-amber/40 disabled:cursor-not-allowed disabled:opacity-50'

export function RunBacktestForm({
  onSuccess,
  onCancel,
}: RunBacktestFormProps): React.JSX.Element {
  const [strategyId, setStrategyId] = useState('')
  const [backtestName, setBacktestName] = useState('')

  // Both dates are derived from the same `now` snapshot to avoid
  // edge-case inconsistencies when the component mounts near midnight.
  const [startDate, setStartDate] = useState<string>(() => {
    const now = new Date()
    const threeYearsAgo = new Date(now)
    threeYearsAgo.setFullYear(threeYearsAgo.getFullYear() - 3)
    return threeYearsAgo.toISOString().split('T')[0]
  })
  const [endDate, setEndDate] = useState<string>(() => {
    const now = new Date()
    return now.toISOString().split('T')[0]
  })
  const [initialCash, setInitialCash] = useState('10000')
  const [errors, setErrors] = useState<Record<string, string>>({})

  // today is the initial endDate value — used as max for date inputs
  const today = endDate

  const { data: strategiesPage, isLoading: loadingStrategies } = useStrategies()
  const strategies = strategiesPage?.items
  const runBacktest = useRunBacktest()

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {}

    if (!strategyId) {
      newErrors.strategyId = 'Please select a strategy'
    }
    if (!backtestName.trim()) {
      newErrors.backtestName = 'Backtest name is required'
    }
    if (!startDate) {
      newErrors.startDate = 'Start date is required'
    }
    if (!endDate) {
      newErrors.endDate = 'End date is required'
    }
    if (startDate && endDate) {
      const start = new Date(startDate)
      const end = new Date(endDate)
      const now = new Date()

      if (end <= start) {
        newErrors.endDate = 'End date must be after start date'
      } else if (end > now) {
        newErrors.endDate = 'End date cannot be in the future'
      } else {
        const diffMs = end.getTime() - start.getTime()
        const diffYears = diffMs / (365 * 24 * 60 * 60 * 1000)
        if (diffYears > 3) {
          newErrors.endDate = 'Date range cannot exceed 3 years'
        }
      }
    }

    const cash = parseFloat(initialCash)
    if (!Number.isFinite(cash) || cash <= 0) {
      newErrors.initialCash = 'Initial cash must be a positive number'
    }

    setErrors(newErrors)
    return Object.keys(newErrors).length === 0
  }

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault()
    if (!validate()) return

    runBacktest.mutate(
      {
        strategy_id: strategyId,
        backtest_name: backtestName.trim(),
        start_date: startDate,
        end_date: endDate,
        initial_cash: parseFloat(initialCash),
      },
      {
        onSuccess: () => {
          toast.success('Backtest started')
          onSuccess()
        },
        onError: () => {
          toast.error('Failed to run backtest')
        },
      }
    )
  }

  return (
    <Panel>
      <header className="mb-5">
        <Eyebrow>New backtest</Eyebrow>
        <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
          Run backtest
        </h2>
      </header>
      <form
        onSubmit={handleSubmit}
        data-testid="run-backtest-form"
        className="space-y-4"
      >
        {/* Strategy */}
        <div className="space-y-1.5">
          <Label htmlFor="backtest-strategy">Strategy</Label>
          {loadingStrategies ? (
            <LoadingSpinner size="sm" />
          ) : (
            <select
              id="backtest-strategy"
              data-testid="backtest-strategy-select"
              value={strategyId}
              onChange={(e) => setStrategyId(e.target.value)}
              className={SELECT_CLASSES}
            >
              <option value="">Select a strategy...</option>
              {strategies?.map((s) => (
                <option key={s.id} value={s.id}>
                  {s.name}
                </option>
              ))}
            </select>
          )}
          {errors.strategyId && (
            <p className="text-body-sm text-loss">{errors.strategyId}</p>
          )}
        </div>

        {/* Backtest name */}
        <div className="space-y-1.5">
          <Label htmlFor="backtest-name">Backtest name</Label>
          <Input
            id="backtest-name"
            data-testid="backtest-name-input"
            value={backtestName}
            onChange={(e) => setBacktestName(e.target.value)}
            placeholder="My backtest run"
          />
          {errors.backtestName && (
            <p className="text-body-sm text-loss">{errors.backtestName}</p>
          )}
        </div>

        {/* Date range */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="space-y-1.5">
            <Label htmlFor="backtest-start-date">Start date</Label>
            <Input
              id="backtest-start-date"
              data-testid="backtest-start-date-input"
              type="date"
              value={startDate}
              onChange={(e) => setStartDate(e.target.value)}
              max={today}
            />
            {errors.startDate && (
              <p className="text-body-sm text-loss">{errors.startDate}</p>
            )}
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="backtest-end-date">End date</Label>
            <Input
              id="backtest-end-date"
              data-testid="backtest-end-date-input"
              type="date"
              value={endDate}
              onChange={(e) => setEndDate(e.target.value)}
              max={today}
            />
            {errors.endDate && (
              <p className="text-body-sm text-loss">{errors.endDate}</p>
            )}
          </div>
        </div>

        {/* Initial cash */}
        <div className="space-y-1.5">
          <Label htmlFor="backtest-initial-cash">Initial cash ($)</Label>
          <Input
            id="backtest-initial-cash"
            data-testid="backtest-initial-cash-input"
            type="number"
            min="1"
            step="0.01"
            value={initialCash}
            onChange={(e) => setInitialCash(e.target.value)}
            placeholder="10000"
          />
          {errors.initialCash && (
            <p className="text-body-sm text-loss">{errors.initialCash}</p>
          )}
        </div>

        {/* Actions */}
        <div className="flex justify-end gap-2 pt-2">
          <Button
            type="button"
            variant="ghost"
            onClick={onCancel}
            data-testid="run-backtest-cancel"
          >
            Cancel
          </Button>
          <Button
            type="submit"
            data-testid="run-backtest-submit"
            disabled={runBacktest.isPending}
          >
            {runBacktest.isPending ? 'Running...' : 'Run backtest'}
          </Button>
        </div>
      </form>
    </Panel>
  )
}
