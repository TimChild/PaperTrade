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

    // Editorial restrained radius. Was `rounded-lg` pre-revamp.
    const dialog = container.querySelector('dialog')
    expect(dialog).toBeInTheDocument()
    expect(dialog).toHaveClass('rounded-editorial')
  })

  it('does not render children when isOpen is false', () => {
    // The <dialog> element itself stays mounted (preserves focus-trap +
    // a11y semantics) but the subtree is gated on isOpen — so side-effects
    // in children (TanStack mutations, queries, useEffect) don't fire
    // while the dialog is closed.
    render(
      <Dialog isOpen={false} onClose={vi.fn()}>
        <div data-testid="dialog-child">Hidden child</div>
      </Dialog>
    )

    expect(screen.queryByTestId('dialog-child')).not.toBeInTheDocument()
    expect(screen.queryByText('Hidden child')).not.toBeInTheDocument()
  })

  it('does not render the title header when isOpen is false', () => {
    render(
      <Dialog isOpen={false} onClose={vi.fn()} title="Should not appear">
        <div>Child</div>
      </Dialog>
    )

    expect(screen.queryByText('Should not appear')).not.toBeInTheDocument()
    expect(screen.queryByRole('heading')).not.toBeInTheDocument()
  })

  it('keeps the dialog wrapper element mounted even when isOpen is false', () => {
    // The wrapper stays mounted so focus-trap / a11y semantics persist —
    // only the children get gated. Verify the <dialog> element is in DOM
    // either way.
    const { container, rerender } = render(
      <Dialog isOpen={false} onClose={vi.fn()}>
        <div>Child</div>
      </Dialog>
    )

    expect(container.querySelector('dialog')).toBeInTheDocument()

    rerender(
      <Dialog isOpen={true} onClose={vi.fn()}>
        <div>Child</div>
      </Dialog>
    )

    expect(container.querySelector('dialog')).toBeInTheDocument()
  })

  it('does not render children on first mount when isOpen starts false', () => {
    // Render-counter sentinel: a top-level spy is incremented on every
    // render of the child, so the test can assert that "child not
    // rendered" really means the component function never ran — not
    // just that we couldn't find it in DOM.
    const renderSpy = vi.fn()

    function CountingChild(): React.JSX.Element {
      renderSpy()
      return <div data-testid="counting-child">rendered</div>
    }

    render(
      <Dialog isOpen={false} onClose={vi.fn()}>
        <CountingChild />
      </Dialog>
    )

    // The child component should not have rendered at all.
    expect(renderSpy).not.toHaveBeenCalled()
    expect(screen.queryByTestId('counting-child')).not.toBeInTheDocument()
  })

  it('renders children only after isOpen flips to true', () => {
    const renderSpy = vi.fn()

    function CountingChild(): React.JSX.Element {
      renderSpy()
      return <div data-testid="counting-child">rendered</div>
    }

    const { rerender } = render(
      <Dialog isOpen={false} onClose={vi.fn()}>
        <CountingChild />
      </Dialog>
    )

    // While closed, the child has not rendered.
    expect(renderSpy).not.toHaveBeenCalled()

    rerender(
      <Dialog isOpen={true} onClose={vi.fn()}>
        <CountingChild />
      </Dialog>
    )

    // Now it should have rendered exactly once.
    expect(renderSpy).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('counting-child')).toBeInTheDocument()
  })
})
