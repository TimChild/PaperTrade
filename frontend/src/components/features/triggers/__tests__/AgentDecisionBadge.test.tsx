/**
 * Tests for AgentDecisionBadge.
 *
 * Editorial palette per the G-1 task spec:
 *
 *   BUY               → text-gain
 *   SELL              → text-loss
 *   HOLD              → text-ink-subtle
 *   MODIFY            → text-amber
 *   NEEDS_HUMAN       → bg-amber-soft (pill)
 *   INVOCATION_FAILED → bg-loss-soft (pill)
 */
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { AgentDecisionBadge } from '../AgentDecisionBadge'
import type { AgentDecision } from '@/services/api/types'

describe('AgentDecisionBadge', () => {
  const cases: Array<{
    decision: AgentDecision
    label: string
    classFragment: string
  }> = [
    { decision: 'BUY', label: 'Buy', classFragment: 'text-gain' },
    { decision: 'SELL', label: 'Sell', classFragment: 'text-loss' },
    { decision: 'HOLD', label: 'Hold', classFragment: 'text-ink-subtle' },
    { decision: 'MODIFY', label: 'Modify', classFragment: 'text-amber' },
    {
      decision: 'NEEDS_HUMAN',
      label: 'Needs human',
      classFragment: 'bg-amber-soft',
    },
    {
      decision: 'INVOCATION_FAILED',
      label: 'Invocation failed',
      classFragment: 'bg-loss-soft',
    },
  ]

  it.each(cases)(
    'renders %s with the right label, palette and test id',
    ({ decision, label, classFragment }) => {
      render(<AgentDecisionBadge decision={decision} />)
      const badge = screen.getByTestId(`agent-decision-${decision}`)
      expect(badge).toHaveTextContent(label)
      expect(badge.className).toContain(classFragment)
      expect(badge.getAttribute('role')).toBe('status')
      expect(badge.getAttribute('aria-label')).toBe(`Agent decision: ${label}`)
    }
  )
})
