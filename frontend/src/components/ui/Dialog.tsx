/**
 * Dialog/Modal component
 * Simple modal dialog with backdrop
 */
import { useEffect, useRef } from 'react'

interface DialogProps {
  isOpen: boolean
  onClose: () => void
  title?: string
  children: React.ReactNode
  className?: string
}

export function Dialog({ isOpen, onClose, title, children, className = '' }: DialogProps) {
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

    const handleClose = () => {
      onClose()
    }

    const handleEscape = (e: KeyboardEvent) => {
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

  const handleBackdropClick = (e: React.MouseEvent<HTMLDialogElement>) => {
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
      className={`rounded-lg border-0 bg-white p-6 shadow-xl backdrop:bg-black backdrop:bg-opacity-50 dark:bg-gray-800 ${className}`}
    >
      {title && (
        <h2 className="mb-4 text-xl font-semibold text-gray-900 dark:text-white">{title}</h2>
      )}
      <div>{children}</div>
    </dialog>
  )
}
