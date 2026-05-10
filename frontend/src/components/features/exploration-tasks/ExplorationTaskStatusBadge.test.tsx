import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { ExplorationTaskStatusBadge } from './ExplorationTaskStatusBadge'

describe('ExplorationTaskStatusBadge', () => {
  it('renders a label for OPEN', () => {
    render(<ExplorationTaskStatusBadge status="OPEN" />)
    expect(
      screen.getByTestId('exploration-task-status-OPEN')
    ).toHaveTextContent('Open')
  })

  it('labels IN_PROGRESS as "Claimed"', () => {
    render(<ExplorationTaskStatusBadge status="IN_PROGRESS" />)
    expect(
      screen.getByTestId('exploration-task-status-IN_PROGRESS')
    ).toHaveTextContent('Claimed')
  })

  it('renders DONE with the gain palette classnames', () => {
    render(<ExplorationTaskStatusBadge status="DONE" />)
    const el = screen.getByTestId('exploration-task-status-DONE')
    expect(el).toHaveTextContent('Done')
    expect(el.className).toContain('bg-gain-soft')
    expect(el.className).toContain('text-gain')
  })

  it('renders ABANDONED with the loss palette classnames', () => {
    render(<ExplorationTaskStatusBadge status="ABANDONED" />)
    const el = screen.getByTestId('exploration-task-status-ABANDONED')
    expect(el).toHaveTextContent('Abandoned')
    expect(el.className).toContain('bg-loss-soft')
    expect(el.className).toContain('text-loss')
  })

  it('exposes an aria-label for accessibility', () => {
    render(<ExplorationTaskStatusBadge status="OPEN" />)
    expect(
      screen.getByLabelText('Exploration task status: Open')
    ).toBeInTheDocument()
  })
})
