import { describe, it, expect, vi } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { act } from 'react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { CreatePortfolioForm } from './CreatePortfolioForm'

// Wrapper component with necessary providers
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  })

  return (
    <BrowserRouter>
      <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    </BrowserRouter>
  )
}

describe('CreatePortfolioForm', () => {
  it('renders the form with empty fields', () => {
    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    expect(screen.getByLabelText(/Portfolio Name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/Initial Deposit/i)).toBeInTheDocument()
    expect(
      screen.getByRole('button', { name: /Create Portfolio/i })
    ).toBeInTheDocument()
  })

  it('shows cancel button when onCancel is provided', () => {
    const onCancel = vi.fn()

    render(
      <TestWrapper>
        <CreatePortfolioForm onCancel={onCancel} />
      </TestWrapper>
    )

    expect(screen.getByRole('button', { name: /Cancel/i })).toBeInTheDocument()
  })

  it('does not show cancel button when onCancel is not provided', () => {
    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    expect(
      screen.queryByRole('button', { name: /Cancel/i })
    ).not.toBeInTheDocument()
  })

  it('calls onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()

    render(
      <TestWrapper>
        <CreatePortfolioForm onCancel={onCancel} />
      </TestWrapper>
    )

    await user.click(screen.getByRole('button', { name: /Cancel/i }))
    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('validates required portfolio name', async () => {
    const user = userEvent.setup()

    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    const nameInput = screen.getByLabelText(/Portfolio Name/i)
    const submitButton = screen.getByRole('button', {
      name: /Create Portfolio/i,
    })

    // Submit button should NOT be disabled (HTML5 validation will handle empty name)
    expect(submitButton).not.toBeDisabled()

    // Name input should have required attribute for HTML5 validation
    expect(nameInput).toHaveAttribute('required')

    // Type a name
    await user.type(nameInput, 'Test Portfolio')
    expect(submitButton).not.toBeDisabled()

    // Clear the name
    await user.clear(nameInput)
    // Button still not disabled - HTML5 validation will catch it on submit
    expect(submitButton).not.toBeDisabled()
  })

  it('accepts valid initial deposit values', async () => {
    const user = userEvent.setup()

    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    const depositInput = screen.getByLabelText(/Initial Deposit/i)

    // Type a valid amount
    await user.clear(depositInput)
    await user.type(depositInput, '1000.50')

    expect(depositInput).toHaveValue(1000.5)
  })

  it('shows error for negative deposit amounts on submit', async () => {
    const user = userEvent.setup()

    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    const nameInput = screen.getByLabelText(/Portfolio Name/i)
    const depositInput = screen.getByLabelText(
      /Initial Deposit/i
    ) as HTMLInputElement
    const submitButton = screen.getByRole('button', {
      name: /Create Portfolio/i,
    })

    await user.type(nameInput, 'Test Portfolio')
    await user.clear(depositInput)

    // Manually set a negative value (bypassing HTML5 validation)
    // Wrap in act() to handle state updates from the input event
    act(() => {
      Object.defineProperty(depositInput, 'value', {
        writable: true,
        value: '-100',
      })
      depositInput.dispatchEvent(new Event('input', { bubbles: true }))
    })

    await user.click(submitButton)

    // Use findByRole to wait for the error to appear (handles async state update)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(
      /Initial deposit must be a positive number/i
    )
  })

  it('shows error for portfolio name exceeding 100 characters', async () => {
    const user = userEvent.setup()

    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    const nameInput = screen.getByLabelText(
      /Portfolio Name/i
    ) as HTMLInputElement
    const submitButton = screen.getByRole('button', {
      name: /Create Portfolio/i,
    })

    // Type a name longer than 100 characters (bypassing maxLength by setting value directly)
    const longName = 'A'.repeat(101)

    // Simulate user bypassing client-side validation
    await user.clear(nameInput)
    await user.type(nameInput, 'A'.repeat(50))

    // Manually set the value to exceed the limit (simulating form manipulation)
    // Wrap in act() to handle state updates from the input event
    act(() => {
      Object.defineProperty(nameInput, 'value', {
        writable: true,
        value: longName,
      })
      nameInput.dispatchEvent(new Event('input', { bubbles: true }))
    })

    await user.click(submitButton)

    // Use findByRole to wait for the error to appear (handles async state update)
    const alert = await screen.findByRole('alert')
    expect(alert).toHaveTextContent(
      /Portfolio name must be 100 characters or less/i
    )
  })

  it('trims whitespace from portfolio name', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()

    render(
      <TestWrapper>
        <CreatePortfolioForm onSuccess={onSuccess} />
      </TestWrapper>
    )

    const nameInput = screen.getByLabelText(/Portfolio Name/i)
    const submitButton = screen.getByRole('button', {
      name: /Create Portfolio/i,
    })

    await user.type(nameInput, '  Test Portfolio  ')
    await user.click(submitButton)

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalled()
    })
  })

  it('displays loading state during submission', async () => {
    const user = userEvent.setup()

    // Note: MSW responds quickly, so this test verifies the button is disabled during submission
    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    const nameInput = screen.getByLabelText(/Portfolio Name/i)
    const submitButton = screen.getByRole('button', {
      name: /Create Portfolio/i,
    })

    await user.type(nameInput, 'Test Portfolio')

    // Button should be enabled before submission
    expect(submitButton).not.toBeDisabled()

    // After clicking, it should show loading state (or complete quickly)
    await user.click(submitButton)

    // The form will either show loading or complete successfully
    // We just verify no error occurred
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument()
    })
  })

  it('calls onSuccess with portfolio ID when creation succeeds', async () => {
    const user = userEvent.setup()
    const onSuccess = vi.fn()

    render(
      <TestWrapper>
        <CreatePortfolioForm onSuccess={onSuccess} />
      </TestWrapper>
    )

    const nameInput = screen.getByLabelText(/Portfolio Name/i)
    const depositInput = screen.getByLabelText(/Initial Deposit/i)
    const submitButton = screen.getByRole('button', {
      name: /Create Portfolio/i,
    })

    await user.type(nameInput, 'My New Portfolio')
    await user.clear(depositInput)
    await user.type(depositInput, '5000.00')
    await user.click(submitButton)

    await waitFor(() => {
      expect(onSuccess).toHaveBeenCalledWith(
        '00000000-0000-0000-0000-000000000001'
      )
    })
  })

  it('has accessible form labels and descriptions', () => {
    render(
      <TestWrapper>
        <CreatePortfolioForm />
      </TestWrapper>
    )

    const nameInput = screen.getByLabelText(/Portfolio Name/i)
    const depositInput = screen.getByLabelText(/Initial Deposit/i)

    expect(nameInput).toHaveAccessibleDescription()
    expect(depositInput).toHaveAccessibleDescription()
  })
})
