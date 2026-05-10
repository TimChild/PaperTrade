/**
 * Tests for ActivationStatusBadge.
 *
 * Editorial palette: muted gain / amber soft / ink-subtle / muted loss.
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ActivationStatusBadge } from '../ActivationStatusBadge'
import type { ActivationStatus } from '@/services/api/types'

describe('ActivationStatusBadge', () => {
  const cases: Array<{
    status: ActivationStatus
    label: string
    classFragment: string
  }> = [
    { status: 'ACTIVE', label: 'Active', classFragment: 'bg-gain-soft' },
    { status: 'PAUSED', label: 'Paused', classFragment: 'bg-amber-soft' },
    { status: 'STOPPED', label: 'Stopped', classFragment: 'text-ink-subtle' },
    { status: 'ERROR', label: 'Error', classFragment: 'bg-loss-soft' },
  ]

  it.each(cases)(
    'renders %s with the right label, color and test id',
    ({ status, label, classFragment }) => {
      render(<ActivationStatusBadge status={status} />)
      const badge = screen.getByTestId(`activation-status-${status}`)
      expect(badge).toHaveTextContent(label)
      expect(badge.className).toContain(classFragment)
      // Accessibility: role + aria-label.
      expect(badge.getAttribute('role')).toBe('status')
      expect(badge.getAttribute('aria-label')).toBe(
        `Activation status: ${label}`
      )
    }
  )

  it('passes through extra className', () => {
    render(<ActivationStatusBadge status="ACTIVE" className="extra-class" />)
    expect(screen.getByTestId('activation-status-ACTIVE').className).toContain(
      'extra-class'
    )
  })
})
