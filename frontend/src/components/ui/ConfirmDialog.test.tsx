import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ConfirmDialog } from './ConfirmDialog'

describe('ConfirmDialog', () => {
  it('should not render when isOpen is false', () => {
    render(
      <ConfirmDialog
        isOpen={false}
        title="Test Title"
        message="Test message"
        confirmLabel="Confirm"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )

    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument()
  })

  it('should render when isOpen is true', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Test Title"
        message="Test message"
        confirmLabel="Confirm"
        onConfirm={() => {}}
        onCancel={() => {}}
      />
    )

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.getByText('Test message')).toBeInTheDocument()
  })

  it('should call onConfirm when confirm button is clicked', async () => {
    const user = userEvent.setup()
    const onConfirm = vi.fn()

    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Item"
        message="Are you sure?"
        confirmLabel="Delete"
        onConfirm={onConfirm}
        onCancel={() => {}}
      />
    )

    await user.click(screen.getByTestId('confirm-dialog-confirm'))

    expect(onConfirm).toHaveBeenCalledTimes(1)
  })

  it('should call onCancel when cancel button is clicked', async () => {
    const user = userEvent.setup()
    const onCancel = vi.fn()

    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Item"
        message="Are you sure?"
        confirmLabel="Delete"
        onConfirm={() => {}}
        onCancel={onCancel}
      />
    )

    await user.click(screen.getByTestId('confirm-dialog-cancel'))

    expect(onCancel).toHaveBeenCalledTimes(1)
  })

  it('should apply danger variant styles', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Item"
        message="Are you sure?"
        confirmLabel="Delete"
        onConfirm={() => {}}
        onCancel={() => {}}
        variant="danger"
      />
    )

    const confirmButton = screen.getByTestId('confirm-dialog-confirm')
    expect(confirmButton).toHaveClass('bg-red-600')
  })

  it('should disable buttons when isLoading is true', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Item"
        message="Are you sure?"
        confirmLabel="Delete"
        onConfirm={() => {}}
        onCancel={() => {}}
        isLoading={true}
      />
    )

    expect(screen.getByTestId('confirm-dialog-confirm')).toBeDisabled()
    expect(screen.getByTestId('confirm-dialog-cancel')).toBeDisabled()
  })

  it('should show loading text when isLoading is true', () => {
    render(
      <ConfirmDialog
        isOpen={true}
        title="Delete Item"
        message="Are you sure?"
        confirmLabel="Delete"
        onConfirm={() => {}}
        onCancel={() => {}}
        isLoading={true}
      />
    )

    expect(screen.getByText('Processing...')).toBeInTheDocument()
  })
})
