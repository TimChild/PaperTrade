/**
 * Tests for ComparisonTable component
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ComparisonTable } from '../ComparisonTable'
import type { BacktestRunResponse } from '@/services/api/types'

const makeBacktest = (
  overrides: Partial<BacktestRunResponse>
): BacktestRunResponse => ({
  id: 'bt-1',
  user_id: 'user-1',
  strategy_id: 'strategy-1',
  portfolio_id: 'portfolio-1',
  backtest_name: 'Backtest 1',
  start_date: '2023-01-01',
  end_date: '2024-01-01',
  initial_cash: '10000.00',
  status: 'COMPLETED',
  created_at: '2024-01-01T00:00:00Z',
  completed_at: '2024-01-01T01:00:00Z',
  error_message: null,
  total_return_pct: '20.00',
  max_drawdown_pct: '-5.00',
  annualized_return_pct: '20.00',
  total_trades: 10,
  ...overrides,
})

const strategyNames: Record<string, string> = {
  'strategy-1': 'Buy & Hold',
  'strategy-2': 'DCA Strategy',
}

describe('ComparisonTable', () => {
  it('renders empty state when no backtests provided', () => {
    render(<ComparisonTable backtests={[]} strategyNames={{}} />)

    expect(screen.getByTestId('comparison-table-empty')).toBeInTheDocument()
  })

  it('renders table with backtest data', () => {
    const backtests = [makeBacktest({ id: 'bt-1', backtest_name: 'Test A' })]
    render(
      <ComparisonTable backtests={backtests} strategyNames={strategyNames} />
    )

    expect(screen.getByTestId('comparison-table')).toBeInTheDocument()
    expect(screen.getByText('Test A')).toBeInTheDocument()
  })

  it('renders correct rows', () => {
    const backtests = [makeBacktest({ id: 'bt-1' })]
    render(
      <ComparisonTable backtests={backtests} strategyNames={strategyNames} />
    )

    expect(screen.getByText('Strategy')).toBeInTheDocument()
    expect(screen.getByText('Date Range')).toBeInTheDocument()
    expect(screen.getByText('Initial Cash')).toBeInTheDocument()
    expect(screen.getByText('Total Return')).toBeInTheDocument()
    expect(screen.getByText('Annualized Return')).toBeInTheDocument()
    expect(screen.getByText('Max Drawdown')).toBeInTheDocument()
    expect(screen.getByText('Total Trades')).toBeInTheDocument()
  })

  it('renders strategy name from strategyNames lookup', () => {
    const backtests = [makeBacktest({ id: 'bt-1', strategy_id: 'strategy-1' })]
    render(
      <ComparisonTable backtests={backtests} strategyNames={strategyNames} />
    )

    expect(screen.getByText('Buy & Hold')).toBeInTheDocument()
  })

  it('applies best/worst coloring for total return', () => {
    const backtests = [
      makeBacktest({
        id: 'bt-1',
        backtest_name: 'Low Return',
        total_return_pct: '5.00',
      }),
      makeBacktest({
        id: 'bt-2',
        backtest_name: 'High Return',
        total_return_pct: '25.00',
      }),
    ]
    render(
      <ComparisonTable backtests={backtests} strategyNames={strategyNames} />
    )

    const bestCell = screen.getByTestId('total-return-bt-2')
    const worstCell = screen.getByTestId('total-return-bt-1')

    expect(bestCell.className).toContain('bg-green-50')
    expect(worstCell.className).toContain('bg-red-50')
  })

  it('applies best coloring for max drawdown (closest to 0 is best)', () => {
    const backtests = [
      makeBacktest({
        id: 'bt-1',
        backtest_name: 'Shallow Drawdown',
        max_drawdown_pct: '-2.00',
      }),
      makeBacktest({
        id: 'bt-2',
        backtest_name: 'Deep Drawdown',
        max_drawdown_pct: '-15.00',
      }),
    ]
    render(
      <ComparisonTable backtests={backtests} strategyNames={strategyNames} />
    )

    const bestCell = screen.getByTestId('max-drawdown-bt-1')
    const worstCell = screen.getByTestId('max-drawdown-bt-2')

    expect(bestCell.className).toContain('bg-green-50')
    expect(worstCell.className).toContain('bg-red-50')
  })

  it('shows --- for null metric values', () => {
    const backtests = [
      makeBacktest({
        id: 'bt-1',
        total_return_pct: null,
        annualized_return_pct: null,
        max_drawdown_pct: null,
        total_trades: null,
      }),
    ]
    render(
      <ComparisonTable backtests={backtests} strategyNames={strategyNames} />
    )

    const totalReturnCell = screen.getByTestId('total-return-bt-1')
    expect(totalReturnCell).toHaveTextContent('---')
  })

  it('renders multiple backtests side by side', () => {
    const backtests = [
      makeBacktest({ id: 'bt-1', backtest_name: 'Strategy A' }),
      makeBacktest({ id: 'bt-2', backtest_name: 'Strategy B' }),
    ]
    render(
      <ComparisonTable backtests={backtests} strategyNames={strategyNames} />
    )

    expect(screen.getByText('Strategy A')).toBeInTheDocument()
    expect(screen.getByText('Strategy B')).toBeInTheDocument()
  })
})
