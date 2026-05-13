/**
 * Editorial dialog — canvas-raised panel with hairline border, eyebrow +
 * display-serif heading. Uses the native `<dialog>` element with
 * `showModal()` for keyboard / focus-trap / ESC-close mechanics.
 *
 * Children render only when `isOpen` is true. The native `<dialog>` element
 * itself stays mounted (so focus-trap and a11y semantics persist), but its
 * subtree is gated on the open state — this prevents side-effects in
 * children (TanStack mutations, queries, `useEffect`) from firing on first
 * render while the dialog is closed, and keeps hidden `<option>` rows etc.
 * out of DOM where they would otherwise be matched by host-page E2E tests.
 * See `docs/planning/agent-platform-next-steps.md` §1.3 for the original
 * `AskAnAgentButton` workaround that motivated this refactor.
 */
import { useEffect, useRef } from 'react'
import { Eyebrow } from './Eyebrow'

interface DialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  /** Optional eyebrow above the title (defaults to "Edit"). */
  eyebrow?: string
  children: React.ReactNode
  className?: string
}

export function Dialog({
  isOpen,
  onClose,
  title,
  eyebrow = 'Edit',
  children,
  className = '',
}: DialogProps): React.JSX.Element {
  const dialogRef = useRef<HTMLDialogElement>(null)

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    if (isOpen) {
      dialog.showModal()
    } else {
      dialog.close()
    }
  }, [isOpen])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!dialog) return

    const handleClose = (): void => {
      onClose()
    }

    const handleEscape = (e: KeyboardEvent): void => {
      if (e.key === 'Escape') {
        onClose()
      }
    }

    dialog.addEventListener('close', handleClose)
    dialog.addEventListener('keydown', handleEscape)

    return () => {
      dialog.removeEventListener('close', handleClose)
      dialog.removeEventListener('keydown', handleEscape)
    }
  }, [onClose])

  const handleBackdropClick = (
    e: React.MouseEvent<HTMLDialogElement>
  ): void => {
    const dialog = dialogRef.current
    if (!dialog) return

    const rect = dialog.getBoundingClientRect()
    const isInDialog =
      rect.top <= e.clientY &&
      e.clientY <= rect.top + rect.height &&
      rect.left <= e.clientX &&
      e.clientX <= rect.left + rect.width

    if (!isInDialog) {
      onClose()
    }
  }

  return (
    <dialog
      ref={dialogRef}
      onClick={handleBackdropClick}
      data-testid="dialog"
      className={`rounded-editorial border border-hairline bg-canvas-raised text-ink p-6 shadow-elevated backdrop:bg-canvas-sunken/80 backdrop:backdrop-blur-sm ${className}`}
    >
      {isOpen && (
        <>
          {title && (
            <header className="mb-5">
              <Eyebrow>{eyebrow}</Eyebrow>
              <h2 className="mt-1.5 font-display text-display-sm tracking-tight text-ink">
                {title}
              </h2>
            </header>
          )}
          <div>{children}</div>
        </>
      )}
    </dialog>
  )
}
