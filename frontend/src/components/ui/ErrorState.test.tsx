import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ErrorState } from './ErrorState'

describe('ErrorState', () => {
  it('should render with default title and message', () => {
    render(<ErrorState message="An error occurred" />)

    expect(screen.getByText('Something went wrong')).toBeInTheDocument()
    expect(screen.getByText('An error occurred')).toBeInTheDocument()
  })

  it('should render with custom title', () => {
    render(<ErrorState title="Custom Error" message="Error details" />)

    expect(screen.getByText('Custom Error')).toBeInTheDocument()
    expect(screen.getByText('Error details')).toBeInTheDocument()
  })

  it('should render retry button when onRetry is provided', () => {
    const onRetry = vi.fn()

    render(<ErrorState message="Error" onRetry={onRetry} />)

    expect(screen.getByTestId('error-state-retry')).toBeInTheDocument()
    expect(screen.getByText('Try Again')).toBeInTheDocument()
  })

  it('should call onRetry when retry button is clicked', async () => {
    const user = userEvent.setup()
    const onRetry = vi.fn()

    render(<ErrorState message="Error" onRetry={onRetry} />)

    await user.click(screen.getByTestId('error-state-retry'))

    expect(onRetry).toHaveBeenCalledTimes(1)
  })

  it('should render action button when onAction and actionLabel are provided', () => {
    const onAction = vi.fn()

    render(
      <ErrorState
        message="Error"
        onAction={onAction}
        actionLabel="Go Back"
      />
    )

    expect(screen.getByTestId('error-state-action')).toBeInTheDocument()
    expect(screen.getByText('Go Back')).toBeInTheDocument()
  })

  it('should call onAction when action button is clicked', async () => {
    const user = userEvent.setup()
    const onAction = vi.fn()

    render(
      <ErrorState
        message="Error"
        onAction={onAction}
        actionLabel="Go Back"
      />
    )

    await user.click(screen.getByTestId('error-state-action'))

    expect(onAction).toHaveBeenCalledTimes(1)
  })

  it('should render both retry and action buttons when both are provided', () => {
    render(
      <ErrorState
        message="Error"
        onRetry={() => {}}
        onAction={() => {}}
        actionLabel="Cancel"
      />
    )

    expect(screen.getByTestId('error-state-retry')).toBeInTheDocument()
    expect(screen.getByTestId('error-state-action')).toBeInTheDocument()
  })

  it('should not render action button if actionLabel is missing', () => {
    render(<ErrorState message="Error" onAction={() => {}} />)

    expect(screen.queryByTestId('error-state-action')).not.toBeInTheDocument()
  })

  it('should apply custom className', () => {
    render(<ErrorState message="Error" className="custom-class" />)

    const container = screen.getByTestId('error-state')
    expect(container).toHaveClass('custom-class')
  })
})
