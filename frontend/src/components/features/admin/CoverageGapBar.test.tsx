import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { CoverageGapBar } from './CoverageGapBar'

describe('CoverageGapBar', () => {
  it('renders nothing when coverageStart is null', () => {
    const { container } = render(
      <CoverageGapBar
        coverageStart={null}
        coverageEnd="2026-05-01"
        gapRanges={[]}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when coverageEnd is null', () => {
    const { container } = render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd={null}
        gapRanges={[]}
      />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders nothing when both coverage dates are null', () => {
    const { container } = render(
      <CoverageGapBar coverageStart={null} coverageEnd={null} gapRanges={[]} />
    )
    expect(container.firstChild).toBeNull()
  })

  it('renders the SVG with the background band when there are no gaps', () => {
    render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-01"
        gapRanges={[]}
      />
    )
    expect(screen.getByTestId('coverage-gap-bar')).toBeInTheDocument()
    expect(screen.getByTestId('coverage-gap-bar-band')).toBeInTheDocument()
    // No gap rects
    expect(
      screen.queryByTestId('coverage-gap-bar-gap-0')
    ).not.toBeInTheDocument()
  })

  it('renders one gap rect for a single gap range', () => {
    render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-01"
        gapRanges={[{ start: '2026-02-10', end: '2026-02-14' }]}
      />
    )
    expect(screen.getByTestId('coverage-gap-bar-gap-0')).toBeInTheDocument()
    expect(
      screen.queryByTestId('coverage-gap-bar-gap-1')
    ).not.toBeInTheDocument()
  })

  it('renders the correct number of gap rects for multiple gaps', () => {
    render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-01"
        gapRanges={[
          { start: '2026-02-10', end: '2026-02-12' },
          { start: '2026-03-15', end: '2026-03-15' },
          { start: '2026-04-20', end: '2026-04-22' },
        ]}
      />
    )
    expect(screen.getByTestId('coverage-gap-bar-gap-0')).toBeInTheDocument()
    expect(screen.getByTestId('coverage-gap-bar-gap-1')).toBeInTheDocument()
    expect(screen.getByTestId('coverage-gap-bar-gap-2')).toBeInTheDocument()
    expect(
      screen.queryByTestId('coverage-gap-bar-gap-3')
    ).not.toBeInTheDocument()
  })

  it('positions gap rects proportionally within the coverage span', () => {
    render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-01-11"
        gapRanges={[{ start: '2026-01-06', end: '2026-01-06' }]}
      />
    )
    // 2026-01-01 → 2026-01-11 is 10 days. Gap starts at day 5 (50% = 60px).
    const gapRect = screen.getByTestId('coverage-gap-bar-gap-0')
    const x = parseFloat(gapRect.getAttribute('x') ?? '0')
    // Allow ±2px tolerance for date arithmetic
    expect(x).toBeGreaterThan(55)
    expect(x).toBeLessThan(65)
  })

  it('renders a tooltip title for gap ranges', () => {
    const { container } = render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-01"
        gapRanges={[{ start: '2026-04-12', end: '2026-04-12' }]}
      />
    )
    const title = container.querySelector('title')
    expect(title).toBeInTheDocument()
    expect(title?.textContent).toContain('Apr 12, 2026')
  })

  it('renders no tooltip title when there are no gaps', () => {
    const { container } = render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-01"
        gapRanges={[]}
      />
    )
    expect(container.querySelector('title')).not.toBeInTheDocument()
  })

  it('formats a multi-day same-month gap with en dash', () => {
    const { container } = render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-20"
        gapRanges={[{ start: '2026-05-15', end: '2026-05-17' }]}
      />
    )
    const title = container.querySelector('title')
    expect(title?.textContent).toContain('May 15')
    expect(title?.textContent).toContain('17')
    expect(title?.textContent).toContain('2026')
  })

  it('uses aria-label indicating no gaps when gapRanges is empty', () => {
    render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-01"
        gapRanges={[]}
      />
    )
    const svg = screen.getByTestId('coverage-gap-bar')
    expect(svg).toHaveAttribute('aria-label', 'Full coverage — no gaps')
  })

  it('uses aria-label listing gaps when gapRanges is non-empty', () => {
    render(
      <CoverageGapBar
        coverageStart="2026-01-01"
        coverageEnd="2026-05-01"
        gapRanges={[{ start: '2026-04-12', end: '2026-04-12' }]}
      />
    )
    const svg = screen.getByTestId('coverage-gap-bar')
    expect(svg.getAttribute('aria-label')).toContain('Coverage gaps:')
    expect(svg.getAttribute('aria-label')).toContain('Apr 12, 2026')
  })
})
