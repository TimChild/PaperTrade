import { afterEach, describe, expect, it, vi } from 'vitest'
import { act, fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { CreateApiKeyDialog } from './CreateApiKeyDialog'
import type { CreateApiKeyResponse } from '@/services/api/types'

const baseProps = {
  isOpen: true,
  onClose: vi.fn(),
  onSubmit: vi.fn(),
  isPending: false,
  mintResult: null,
  onDone: vi.fn(),
}

const mintResponse: CreateApiKeyResponse = {
  id: '00000000-0000-0000-0000-00000000abcd',
  label: 'claude-code-laptop',
  scopes: ['read', 'trade'],
  raw_key: 'zk_test_abcdef0123456789',
  created_at: '2024-01-01T00:00:00Z',
  expires_at: null,
}

describe('CreateApiKeyDialog — form stage', () => {
  it('returns null when not open', () => {
    const { container } = render(
      <CreateApiKeyDialog {...baseProps} isOpen={false} />
    )

    expect(container.firstChild).toBeNull()
  })

  it('renders the form when open with no mint result', () => {
    render(<CreateApiKeyDialog {...baseProps} />)

    expect(screen.getByTestId('api-key-create-form')).toBeInTheDocument()
    expect(screen.getByTestId('api-key-create-label-input')).toBeInTheDocument()
    expect(screen.getByTestId('api-key-create-scope-read')).toBeChecked()
    expect(screen.getByTestId('api-key-create-scope-trade')).toBeChecked()
    expect(screen.getByTestId('api-key-create-scope-admin')).not.toBeChecked()
  })

  it('shows a label-required error when submitted empty', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<CreateApiKeyDialog {...baseProps} onSubmit={onSubmit} />)

    await user.click(screen.getByTestId('api-key-create-submit-btn'))

    expect(screen.getByTestId('api-key-create-label-error')).toHaveTextContent(
      /required/i
    )
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('refuses to submit when no scopes are selected', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<CreateApiKeyDialog {...baseProps} onSubmit={onSubmit} />)

    await user.type(
      screen.getByTestId('api-key-create-label-input'),
      'agent-bot'
    )
    // Uncheck the two defaults
    await user.click(screen.getByTestId('api-key-create-scope-read'))
    await user.click(screen.getByTestId('api-key-create-scope-trade'))

    await user.click(screen.getByTestId('api-key-create-submit-btn'))

    expect(screen.getByTestId('api-key-create-scopes-error')).toHaveTextContent(
      /at least one/i
    )
    expect(onSubmit).not.toHaveBeenCalled()
  })

  it('caps label length at 64 characters via maxLength', () => {
    render(<CreateApiKeyDialog {...baseProps} />)

    const input = screen.getByTestId(
      'api-key-create-label-input'
    ) as HTMLInputElement
    expect(input).toHaveAttribute('maxLength', '64')
  })

  it('submits with the label, default scopes and null expiry by default', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<CreateApiKeyDialog {...baseProps} onSubmit={onSubmit} />)

    await user.type(
      screen.getByTestId('api-key-create-label-input'),
      '  agent-bot  '
    )
    await user.click(screen.getByTestId('api-key-create-submit-btn'))

    expect(onSubmit).toHaveBeenCalledTimes(1)
    expect(onSubmit).toHaveBeenCalledWith({
      label: 'agent-bot',
      scopes: ['read', 'trade'],
      expiresAt: null,
    })
  })

  it('forwards expiresAt as an end-of-day UTC ISO string', async () => {
    const user = userEvent.setup()
    const onSubmit = vi.fn()

    render(<CreateApiKeyDialog {...baseProps} onSubmit={onSubmit} />)

    await user.type(
      screen.getByTestId('api-key-create-label-input'),
      'temp-bot'
    )
    // type=date inputs need fireEvent.change since userEvent.type can't
    // simulate the full date-picker interaction reliably in jsdom.
    fireEvent.change(screen.getByTestId('api-key-create-expires-input'), {
      target: { value: '2024-12-31' },
    })

    await user.click(screen.getByTestId('api-key-create-submit-btn'))

    expect(onSubmit).toHaveBeenCalledWith({
      label: 'temp-bot',
      scopes: ['read', 'trade'],
      expiresAt: '2024-12-31T23:59:59.000Z',
    })
  })

  it('disables submit and cancel while pending', () => {
    render(<CreateApiKeyDialog {...baseProps} isPending={true} />)

    expect(screen.getByTestId('api-key-create-submit-btn')).toBeDisabled()
    expect(screen.getByTestId('api-key-create-cancel-btn')).toBeDisabled()
    expect(screen.getByTestId('api-key-create-submit-btn')).toHaveTextContent(
      /Creating/i
    )
  })

  it('calls onClose when cancel is clicked', async () => {
    const user = userEvent.setup()
    const onClose = vi.fn()

    render(<CreateApiKeyDialog {...baseProps} onClose={onClose} />)

    await user.click(screen.getByTestId('api-key-create-cancel-btn'))

    expect(onClose).toHaveBeenCalled()
  })
})

describe('CreateApiKeyDialog — mint result stage', () => {
  afterEach(() => {
    vi.useRealTimers()
  })

  it('renders the raw key and metadata after a successful mint', () => {
    render(<CreateApiKeyDialog {...baseProps} mintResult={mintResponse} />)

    expect(screen.getByTestId('api-key-mint-result')).toBeInTheDocument()
    expect(screen.getByTestId('api-key-mint-result-value')).toHaveTextContent(
      mintResponse.raw_key
    )
    expect(screen.getByTestId('api-key-mint-result-label')).toHaveTextContent(
      'claude-code-laptop'
    )
    expect(screen.getByTestId('api-key-mint-result-scopes')).toHaveTextContent(
      'read, trade'
    )
    expect(screen.getByTestId('api-key-mint-result-expires')).toHaveTextContent(
      'Never'
    )
    expect(screen.queryByTestId('api-key-create-form')).not.toBeInTheDocument()
  })

  it('renders the secret in monospace font', () => {
    render(<CreateApiKeyDialog {...baseProps} mintResult={mintResponse} />)

    expect(screen.getByTestId('api-key-mint-result-value')).toHaveClass(
      'font-mono'
    )
  })

  it('warns the user the key cannot be retrieved later', () => {
    render(<CreateApiKeyDialog {...baseProps} mintResult={mintResponse} />)

    expect(
      screen.getByText(/only time you will see this secret/i)
    ).toBeInTheDocument()
  })

  it('copies the secret and flips the button label to "Copied!"', async () => {
    const writeText = vi.fn().mockResolvedValue(undefined)
    Object.defineProperty(navigator, 'clipboard', {
      configurable: true,
      value: { writeText },
    })
    vi.useFakeTimers({ shouldAdvanceTime: true })

    render(<CreateApiKeyDialog {...baseProps} mintResult={mintResponse} />)

    const copyBtn = screen.getByTestId('api-key-mint-result-copy-btn')
    expect(copyBtn).toHaveTextContent('Copy secret')

    fireEvent.click(copyBtn)
    // Let the resolved Promise from clipboard.writeText run
    await act(async () => {
      await Promise.resolve()
    })

    expect(writeText).toHaveBeenCalledWith(mintResponse.raw_key)
    expect(copyBtn).toHaveTextContent('Copied!')

    // Advance past the 1.5s reset window
    await act(async () => {
      vi.advanceTimersByTime(1500)
    })
    expect(copyBtn).toHaveTextContent('Copy secret')
  })

  it('calls onDone when the Done button is clicked', () => {
    const onDone = vi.fn()

    render(
      <CreateApiKeyDialog
        {...baseProps}
        mintResult={mintResponse}
        onDone={onDone}
      />
    )

    fireEvent.click(screen.getByTestId('api-key-mint-result-done-btn'))

    expect(onDone).toHaveBeenCalled()
  })

  it('shows the formatted expiry when expires_at is set', () => {
    render(
      <CreateApiKeyDialog
        {...baseProps}
        mintResult={{
          ...mintResponse,
          expires_at: '2024-12-31T23:59:59.000Z',
        }}
      />
    )

    const expiresElement = screen.getByTestId('api-key-mint-result-expires')
    expect(expiresElement).not.toHaveTextContent('Never')
    expect(expiresElement.textContent?.length).toBeGreaterThan(0)
  })
})
