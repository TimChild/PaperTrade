/**
 * Editorial metrics-comparison table — hairline DataTable primitives,
 * tabular-mono numerics, gain/loss tones for highlighted best/worst cells.
 */
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataRow,
  DataCell,
  DataHeaderCell,
} from '@/components/ui/DataRow'
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
  if (highlight === 'best') return 'bg-gain-soft/60 font-semibold'
  if (highlight === 'worst') return 'bg-loss-soft/60'
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
        className="text-body-sm text-ink-muted"
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
    <DataTable testId="comparison-table">
      <DataTableHead>
        <DataHeaderCell>Metric</DataHeaderCell>
        {backtests.map((b) => (
          <DataHeaderCell key={b.id}>{b.backtest_name}</DataHeaderCell>
        ))}
      </DataTableHead>
      <DataTableBody>
        {/* Strategy Name */}
        <DataRow>
          <DataCell emphasis="primary">Strategy</DataCell>
          {backtests.map((b) => (
            <DataCell key={b.id} tone="muted">
              {b.strategy_id !== null
                ? (strategyNames[b.strategy_id] ?? '—')
                : '—'}
            </DataCell>
          ))}
        </DataRow>

        {/* Date Range */}
        <DataRow>
          <DataCell emphasis="primary">Date range</DataCell>
          {backtests.map((b) => (
            <DataCell key={b.id} tone="muted" numeric>
              {formatDate(b.start_date, false)} –{' '}
              {formatDate(b.end_date, false)}
            </DataCell>
          ))}
        </DataRow>

        {/* Initial Cash */}
        <DataRow>
          <DataCell emphasis="primary">Initial cash</DataCell>
          {backtests.map((b) => (
            <DataCell key={b.id} tone="muted" numeric>
              {formatCurrency(parseFloat(b.initial_cash))}
            </DataCell>
          ))}
        </DataRow>

        {/* Total Return % */}
        <DataRow>
          <DataCell emphasis="primary">Total return</DataCell>
          {backtests.map((b, i) => {
            const val = totalReturnValues[i]
            return (
              <DataCell
                key={b.id}
                numeric
                className={getCellClass(totalReturnHighlights[i])}
                testId={`total-return-${b.id}`}
              >
                {val !== null ? formatPercent(val / 100) : '---'}
              </DataCell>
            )
          })}
        </DataRow>

        {/* Annualized Return % */}
        <DataRow>
          <DataCell emphasis="primary">Annualized return</DataCell>
          {backtests.map((b, i) => {
            const val = annualizedReturnValues[i]
            return (
              <DataCell
                key={b.id}
                numeric
                className={getCellClass(annualizedReturnHighlights[i])}
                testId={`annualized-return-${b.id}`}
              >
                {val !== null ? formatPercent(val / 100) : '---'}
              </DataCell>
            )
          })}
        </DataRow>

        {/* Max Drawdown % */}
        <DataRow>
          <DataCell emphasis="primary">Max drawdown</DataCell>
          {backtests.map((b, i) => {
            const val = maxDrawdownValues[i]
            return (
              <DataCell
                key={b.id}
                numeric
                className={getCellClass(maxDrawdownHighlights[i])}
                testId={`max-drawdown-${b.id}`}
              >
                {val !== null ? formatPercent(val / 100, false) : '---'}
              </DataCell>
            )
          })}
        </DataRow>

        {/* Total Trades */}
        <DataRow>
          <DataCell emphasis="primary">Total trades</DataCell>
          {backtests.map((b) => (
            <DataCell
              key={b.id}
              tone="muted"
              numeric
              testId={`total-trades-${b.id}`}
            >
              {b.total_trades !== null ? b.total_trades : '---'}
            </DataCell>
          ))}
        </DataRow>
      </DataTableBody>
    </DataTable>
  )
}
