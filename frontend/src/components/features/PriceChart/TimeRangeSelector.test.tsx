import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { TimeRangeSelector } from '@/components/features/PriceChart/TimeRangeSelector'

describe('TimeRangeSelector', () => {
  it('renders all time range options', () => {
    const onChange = vi.fn()
    render(<TimeRangeSelector selected="1M" onChange={onChange} />)

    expect(screen.getByText('1D')).toBeInTheDocument()
    expect(screen.getByText('1W')).toBeInTheDocument()
    expect(screen.getByText('1M')).toBeInTheDocument()
    expect(screen.getByText('3M')).toBeInTheDocument()
    expect(screen.getByText('1Y')).toBeInTheDocument()
    expect(screen.getByText('ALL')).toBeInTheDocument()
  })

  it('highlights the selected range', () => {
    const onChange = vi.fn()
    render(<TimeRangeSelector selected="1M" onChange={onChange} />)

    const button = screen.getByLabelText('Show 1M price history')
    expect(button).toHaveAttribute('aria-pressed', 'true')
  })

  it('calls onChange when a range is clicked', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TimeRangeSelector selected="1M" onChange={onChange} />)

    await user.click(screen.getByLabelText('Show 1W price history'))
    expect(onChange).toHaveBeenCalledWith('1W')
  })

  it('does not call onChange when selected range is clicked again', async () => {
    const user = userEvent.setup()
    const onChange = vi.fn()
    render(<TimeRangeSelector selected="1M" onChange={onChange} />)

    await user.click(screen.getByLabelText('Show 1M price history'))
    expect(onChange).toHaveBeenCalledWith('1M')
  })
})
