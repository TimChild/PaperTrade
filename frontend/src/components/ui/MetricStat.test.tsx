import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MetricStat } from './MetricStat'

describe('MetricStat', () => {
  it('renders the label and value', () => {
    render(<MetricStat label="Total Value" value="$156,750.00" />)
    expect(screen.getByText('Total Value')).toBeInTheDocument()
    expect(screen.getByText('$156,750.00')).toBeInTheDocument()
  })

  it('applies the editorial display font class to the value', () => {
    // Verifies our design tokens are wired through — the value must be
    // rendered with `font-display` (Fraunces) and `tabular-nums` so
    // numeric data lines up across stacked stats.
    render(<MetricStat label="Total Value" value="$156,750.00" testId="hero" />)
    const valueEl = screen.getByTestId('hero-value')
    expect(valueEl).toHaveClass('font-display')
    expect(valueEl).toHaveClass('tabular-nums')
  })

  it('renders a positive delta with the gain tone', () => {
    render(
      <MetricStat
        label="Daily Change"
        value="$2,450.00"
        delta={{ value: '+1.59%', tone: 'gain' }}
        testId="daily"
      />
    )
    const delta = screen.getByTestId('daily-delta')
    expect(delta).toHaveClass('text-gain')
    expect(delta).toHaveTextContent('+1.59%')
  })

  it('renders a negative delta with the loss tone', () => {
    render(
      <MetricStat
        label="Daily Change"
        value="-$1,500.00"
        delta={{ value: '-0.96%', tone: 'loss' }}
        testId="loss-stat"
      />
    )
    const delta = screen.getByTestId('loss-stat-delta')
    expect(delta).toHaveClass('text-loss')
  })

  it('renders the secondary delta value when provided', () => {
    render(
      <MetricStat
        label="Daily Change"
        value="$2,450.00"
        delta={{ value: '+$2,450.00', tone: 'gain', secondary: '+1.59%' }}
        testId="combined"
      />
    )
    expect(screen.getByText('+$2,450.00')).toBeInTheDocument()
    expect(screen.getByText('+1.59%')).toBeInTheDocument()
  })

  it('uses hero size classes for the hero variant', () => {
    render(
      <MetricStat
        label="Total Value"
        value="$156,750.00"
        size="hero"
        testId="hero"
      />
    )
    const valueEl = screen.getByTestId('hero-value')
    // Hero size scales up at sm breakpoint. tailwind-merge keeps the
    // responsive variant only when both the base and the sm: cuts collide
    // (custom font-size tokens), so we assert on the responsive form.
    expect(valueEl.className).toMatch(/text-display-(lg|xl)/)
  })

  it('renders an optional caption below the value', () => {
    render(
      <MetricStat
        label="Total Value"
        value="$1,000"
        caption={<span>as of 14:23:08</span>}
      />
    )
    expect(screen.getByText('as of 14:23:08')).toBeInTheDocument()
  })
})
