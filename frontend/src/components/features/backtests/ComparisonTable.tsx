/**
 * Metrics comparison table for multiple backtests
 */
import { formatCurrency, formatPercent, formatDate } from '@/utils/formatters'
import type { BacktestRunResponse } from '@/services/api/types'

interface ComparisonTableProps {
  backtests: BacktestRunResponse[]
  strategyNames: Record<string, string>
}

type HighlightType = 'best' | 'worst' | 'none'

function getReturnHighlights(
  values: (number | null)[],
  higherIsBetter: boolean
): HighlightType[] {
  const validValues = values.filter((v): v is number => v !== null)
  if (validValues.length < 2) return values.map(() => 'none')

  // When higherIsBetter=true, Math.max is the best value.
  // When higherIsBetter=false (lower is better), Math.min is the best value.
  const bestValue = higherIsBetter
    ? Math.max(...validValues)
    : Math.min(...validValues)
  const worstValue = higherIsBetter
    ? Math.min(...validValues)
    : Math.max(...validValues)

  if (bestValue === worstValue) return values.map(() => 'none')

  return values.map((v): HighlightType => {
    if (v === null) return 'none'
    if (v === bestValue) return 'best'
    if (v === worstValue) return 'worst'
    return 'none'
  })
}

function getCellClass(highlight: HighlightType): string {
  if (highlight === 'best')
    return 'bg-green-50 dark:bg-green-900/20 font-semibold'
  if (highlight === 'worst') return 'bg-red-50 dark:bg-red-900/20'
  return ''
}

export function ComparisonTable({
  backtests,
  strategyNames,
}: ComparisonTableProps): React.JSX.Element {
  if (backtests.length === 0) {
    return (
      <p
        data-testid="comparison-table-empty"
        className="text-gray-500 dark:text-gray-400"
      >
        No backtests to compare
      </p>
    )
  }

  const totalReturnValues = backtests.map((b) =>
    b.total_return_pct !== null ? parseFloat(b.total_return_pct) : null
  )
  const annualizedReturnValues = backtests.map((b) =>
    b.annualized_return_pct !== null
      ? parseFloat(b.annualized_return_pct)
      : null
  )
  const maxDrawdownValues = backtests.map((b) =>
    b.max_drawdown_pct !== null ? parseFloat(b.max_drawdown_pct) : null
  )

  const totalReturnHighlights = getReturnHighlights(totalReturnValues, true)
  const annualizedReturnHighlights = getReturnHighlights(
    annualizedReturnValues,
    true
  )
  // For max drawdown, higher (closer to 0) is better (-2% > -15%)
  const maxDrawdownHighlights = getReturnHighlights(maxDrawdownValues, true)

  return (
    <div
      data-testid="comparison-table"
      className="w-full overflow-x-auto rounded-lg border border-gray-200 dark:border-gray-700"
    >
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 bg-gray-50 dark:border-gray-700 dark:bg-gray-800">
            <th className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300">
              Metric
            </th>
            {backtests.map((b) => (
              <th
                key={b.id}
                className="px-4 py-3 text-left font-medium text-gray-600 dark:text-gray-300"
              >
                {b.backtest_name}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {/* Strategy Name */}
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
              Strategy
            </td>
            {backtests.map((b) => (
              <td
                key={b.id}
                className="px-4 py-2 text-gray-600 dark:text-gray-400"
              >
                {b.strategy_id !== null
                  ? (strategyNames[b.strategy_id] ?? '—')
                  : '—'}
              </td>
            ))}
          </tr>

          {/* Date Range */}
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
              Date Range
            </td>
            {backtests.map((b) => (
              <td
                key={b.id}
                className="px-4 py-2 text-gray-600 dark:text-gray-400"
              >
                {formatDate(b.start_date, false)} –{' '}
                {formatDate(b.end_date, false)}
              </td>
            ))}
          </tr>

          {/* Initial Cash */}
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
              Initial Cash
            </td>
            {backtests.map((b) => (
              <td
                key={b.id}
                className="px-4 py-2 text-gray-600 dark:text-gray-400"
              >
                {formatCurrency(parseFloat(b.initial_cash))}
              </td>
            ))}
          </tr>

          {/* Total Return % */}
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
              Total Return
            </td>
            {backtests.map((b, i) => {
              const val = totalReturnValues[i]
              return (
                <td
                  key={b.id}
                  className={`px-4 py-2 ${getCellClass(totalReturnHighlights[i])}`}
                  data-testid={`total-return-${b.id}`}
                >
                  {val !== null ? formatPercent(val / 100) : '---'}
                </td>
              )
            })}
          </tr>

          {/* Annualized Return % */}
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
              Annualized Return
            </td>
            {backtests.map((b, i) => {
              const val = annualizedReturnValues[i]
              return (
                <td
                  key={b.id}
                  className={`px-4 py-2 ${getCellClass(annualizedReturnHighlights[i])}`}
                  data-testid={`annualized-return-${b.id}`}
                >
                  {val !== null ? formatPercent(val / 100) : '---'}
                </td>
              )
            })}
          </tr>

          {/* Max Drawdown % */}
          <tr className="border-b border-gray-100 dark:border-gray-800">
            <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
              Max Drawdown
            </td>
            {backtests.map((b, i) => {
              const val = maxDrawdownValues[i]
              return (
                <td
                  key={b.id}
                  className={`px-4 py-2 ${getCellClass(maxDrawdownHighlights[i])}`}
                  data-testid={`max-drawdown-${b.id}`}
                >
                  {val !== null ? formatPercent(val / 100, false) : '---'}
                </td>
              )
            })}
          </tr>

          {/* Total Trades */}
          <tr>
            <td className="px-4 py-2 font-medium text-gray-700 dark:text-gray-300">
              Total Trades
            </td>
            {backtests.map((b) => (
              <td
                key={b.id}
                className="px-4 py-2 text-gray-600 dark:text-gray-400"
                data-testid={`total-trades-${b.id}`}
              >
                {b.total_trades !== null ? b.total_trades : '---'}
              </td>
            ))}
          </tr>
        </tbody>
      </table>
    </div>
  )
}
