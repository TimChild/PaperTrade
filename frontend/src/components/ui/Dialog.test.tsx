import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Dialog } from './Dialog'

describe('Dialog', () => {
  it('calls showModal when isOpen is true', () => {
    const showModalSpy = vi.spyOn(HTMLDialogElement.prototype, 'showModal')

    render(
      <Dialog isOpen={true} onClose={vi.fn()}>
        <div>Dialog content</div>
      </Dialog>
    )

    expect(showModalSpy).toHaveBeenCalled()
  })

  it('calls close when isOpen is false', () => {
    const closeSpy = vi.spyOn(HTMLDialogElement.prototype, 'close')

    render(
      <Dialog isOpen={false} onClose={vi.fn()}>
        <div>Dialog content</div>
      </Dialog>
    )

    expect(closeSpy).toHaveBeenCalled()
  })

  it('renders title when provided', () => {
    render(
      <Dialog isOpen={true} onClose={vi.fn()} title="Test Dialog">
        <div>Dialog content</div>
      </Dialog>
    )

    expect(screen.getByText('Test Dialog')).toBeInTheDocument()
  })

  it('does not render title when not provided', () => {
    render(
      <Dialog isOpen={true} onClose={vi.fn()}>
        <div>Dialog content</div>
      </Dialog>
    )

    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
  })

  it('renders children content', () => {
    render(
      <Dialog isOpen={true} onClose={vi.fn()}>
        <div>Test content inside dialog</div>
      </Dialog>
    )

    expect(screen.getByText('Test content inside dialog')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(
      <Dialog isOpen={true} onClose={vi.fn()} className="custom-class">
        <div>Content</div>
      </Dialog>
    )

    const dialog = container.querySelector('dialog')
    expect(dialog).toHaveClass('custom-class')
  })

  it('renders dialog element correctly', () => {
    const { container } = render(
      <Dialog isOpen={true} onClose={vi.fn()}>
        <div>Dialog content</div>
      </Dialog>
    )

    const dialog = container.querySelector('dialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveClass('rounded-lg')
  })
})
