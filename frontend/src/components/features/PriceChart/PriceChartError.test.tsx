/**
 * Unit tests for PriceChartError component
 */
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { PriceChartError } from './PriceChartError'
import type { ApiError } from '@/types/errors'

describe('PriceChartError', () => {
  it('renders rate limit error with appropriate icon and message', () => {
    const error: ApiError = {
      type: 'rate_limit',
      message: 'Market data temporarily unavailable due to high demand',
      retryAfter: 60,
    }

    render(<PriceChartError error={error} />)

    expect(screen.getByText('Too Many Requests')).toBeInTheDocument()
    expect(screen.getByText(error.message)).toBeInTheDocument()
    expect(
      screen.getByText('Please try again in 60 seconds')
    ).toBeInTheDocument()
  })

  it('renders server error with appropriate icon and message', () => {
    const error: ApiError = {
      type: 'server_error',
      message: 'Server error occurred',
      details: 'Database connection failed',
    }

    render(<PriceChartError error={error} />)

    expect(screen.getByText('Server Error')).toBeInTheDocument()
    expect(screen.getByText(error.message)).toBeInTheDocument()
  })

  it('renders network error with appropriate icon and message', () => {
    const error: ApiError = {
      type: 'network_error',
      message: 'Unable to connect to server',
    }

    render(<PriceChartError error={error} />)

    expect(screen.getByText('Connection Error')).toBeInTheDocument()
    expect(screen.getByText(error.message)).toBeInTheDocument()
  })

  it('renders not found error with appropriate icon and message', () => {
    const error: ApiError = {
      type: 'not_found',
      message: 'No data found for INVALID',
    }

    render(<PriceChartError error={error} />)

    expect(screen.getByText('Data Not Found')).toBeInTheDocument()
    expect(screen.getByText(error.message)).toBeInTheDocument()
  })

  it('renders unknown error with appropriate icon and message', () => {
    const error: ApiError = {
      type: 'unknown',
      message: 'An unexpected error occurred',
    }

    render(<PriceChartError error={error} />)

    expect(screen.getByText('Something Went Wrong')).toBeInTheDocument()
    expect(screen.getByText(error.message)).toBeInTheDocument()
  })

  it('shows retry button for retriable errors', () => {
    const onRetry = vi.fn()
    const error: ApiError = {
      type: 'server_error',
      message: 'Server error occurred',
    }

    render(<PriceChartError error={error} onRetry={onRetry} />)

    const retryButton = screen.getByRole('button', {
      name: /retry loading price history/i,
    })
    expect(retryButton).toBeInTheDocument()
  })

  it('does not show retry button for not_found errors', () => {
    const onRetry = vi.fn()
    const error: ApiError = {
      type: 'not_found',
      message: 'No data found for INVALID',
    }

    render(<PriceChartError error={error} onRetry={onRetry} />)

    expect(
      screen.queryByRole('button', { name: /retry loading price history/i })
    ).not.toBeInTheDocument()
  })

  it('does not show retry button when onRetry not provided', () => {
    const error: ApiError = {
      type: 'server_error',
      message: 'Server error occurred',
    }

    render(<PriceChartError error={error} />)

    expect(
      screen.queryByRole('button', { name: /retry loading price history/i })
    ).not.toBeInTheDocument()
  })

  it('calls onRetry when retry button is clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()
    const error: ApiError = {
      type: 'server_error',
      message: 'Server error occurred',
    }

    render(<PriceChartError error={error} onRetry={onRetry} />)

    const retryButton = screen.getByRole('button', {
      name: /retry loading price history/i,
    })
    await user.click(retryButton)

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('shows technical details in development mode', () => {
    // Mock development mode
    const originalEnv = import.meta.env.DEV
    import.meta.env.DEV = true

    const error: ApiError = {
      type: 'server_error',
      message: 'Server error occurred',
      details: 'Database connection failed',
    }

    render(<PriceChartError error={error} />)

    expect(screen.getByText('Technical Details')).toBeInTheDocument()

    // Restore original env
    import.meta.env.DEV = originalEnv
  })

  it('displays retry countdown for rate limit errors', () => {
    const error: ApiError = {
      type: 'rate_limit',
      message: 'Too many requests',
      retryAfter: 120,
    }

    render(<PriceChartError error={error} />)

    expect(
      screen.getByText('Please try again in 120 seconds')
    ).toBeInTheDocument()
  })
})
