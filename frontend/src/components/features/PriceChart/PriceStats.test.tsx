import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { PriceStats } from '@/components/features/PriceChart/PriceStats'

describe('PriceStats', () => {
  it('displays current price formatted as currency', () => {
    render(
      <PriceStats currentPrice={150.25} change={5.25} changePercent={3.61} />
    )

    expect(screen.getByText('$150.25')).toBeInTheDocument()
  })

  it('displays positive change with green color and plus sign', () => {
    render(
      <PriceStats currentPrice={150.25} change={5.25} changePercent={3.61} />
    )

    const changeAmount = screen.getByText('+$5.25')
    expect(changeAmount).toBeInTheDocument()
    expect(changeAmount).toHaveClass('text-green-600')

    const changePercent = screen.getByText('+3.61%')
    expect(changePercent).toBeInTheDocument()
    expect(changePercent).toHaveClass('text-green-600')
  })

  it('displays negative change with red color and minus sign', () => {
    render(
      <PriceStats currentPrice={145.0} change={-5.25} changePercent={-3.48} />
    )

    const changeAmount = screen.getByText('-$5.25')
    expect(changeAmount).toBeInTheDocument()
    expect(changeAmount).toHaveClass('text-red-600')

    const changePercent = screen.getByText('-3.48%')
    expect(changePercent).toBeInTheDocument()
    expect(changePercent).toHaveClass('text-red-600')
  })

  it('displays zero change with green color', () => {
    render(<PriceStats currentPrice={150.0} change={0} changePercent={0} />)

    const changeAmount = screen.getByText('+$0.00')
    expect(changeAmount).toBeInTheDocument()
    expect(changeAmount).toHaveClass('text-green-600')

    const changePercent = screen.getByText('+0.00%')
    expect(changePercent).toBeInTheDocument()
  })

  it('formats large numbers correctly', () => {
    render(
      <PriceStats currentPrice={1250.5} change={125.5} changePercent={11.14} />
    )

    expect(screen.getByText('$1,250.50')).toBeInTheDocument()
    expect(screen.getByText('+$125.50')).toBeInTheDocument()
    expect(screen.getByText('+11.14%')).toBeInTheDocument()
  })

  it('displays fallback when currentPrice is undefined', () => {
    render(
      <PriceStats currentPrice={undefined} change={5.25} changePercent={3.61} />
    )

    expect(screen.getByText('---')).toBeInTheDocument()
    expect(screen.getByText('Price data unavailable')).toBeInTheDocument()
  })

  it('displays fallback when change is NaN', () => {
    render(
      <PriceStats currentPrice={150.25} change={NaN} changePercent={3.61} />
    )

    expect(screen.getByText('---')).toBeInTheDocument()
    expect(screen.getByText('Price data unavailable')).toBeInTheDocument()
  })

  it('displays fallback when all values are undefined', () => {
    render(
      <PriceStats
        currentPrice={undefined}
        change={undefined}
        changePercent={undefined}
      />
    )

    expect(screen.getByText('---')).toBeInTheDocument()
    expect(screen.getByText('Price data unavailable')).toBeInTheDocument()
  })
})
