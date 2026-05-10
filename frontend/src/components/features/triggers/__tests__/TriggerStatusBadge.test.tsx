/**
 * Tests for TriggerStatusBadge.
 *
 * Editorial palette per the G-1 task spec:
 *
 *   ACTIVE            → bg-gain-soft (muted gain)
 *   PAUSED            → ink-subtle (dormant but not terminal)
 *   EXPIRED           → ink-faint (terminal, low emphasis)
 *   MANUALLY_DISABLED → bg-loss-soft (kill switch fingerprint)
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TriggerStatusBadge } from '../TriggerStatusBadge'
import type { TriggerStatus } from '@/services/api/types'

describe('TriggerStatusBadge', () => {
  const cases: Array<{
    status: TriggerStatus
    label: string
    classFragment: string
  }> = [
    { status: 'ACTIVE', label: 'Active', classFragment: 'bg-gain-soft' },
    { status: 'PAUSED', label: 'Paused', classFragment: 'text-ink-subtle' },
    { status: 'EXPIRED', label: 'Expired', classFragment: 'text-ink-faint' },
    {
      status: 'MANUALLY_DISABLED',
      label: 'Disabled',
      classFragment: 'bg-loss-soft',
    },
  ]

  it.each(cases)(
    'renders %s with the right label, palette and test id',
    ({ status, label, classFragment }) => {
      render(<TriggerStatusBadge status={status} />)
      const badge = screen.getByTestId(`trigger-status-${status}`)
      expect(badge).toHaveTextContent(label)
      expect(badge.className).toContain(classFragment)
      // Accessibility: role + aria-label.
      expect(badge.getAttribute('role')).toBe('status')
      expect(badge.getAttribute('aria-label')).toBe(`Trigger status: ${label}`)
    }
  )

  it('passes through extra className', () => {
    render(<TriggerStatusBadge status="ACTIVE" className="extra-class" />)
    expect(screen.getByTestId('trigger-status-ACTIVE').className).toContain(
      'extra-class'
    )
  })
})
