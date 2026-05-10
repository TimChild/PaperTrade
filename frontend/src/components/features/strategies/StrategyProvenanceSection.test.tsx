/**
 * Tests for the strategy provenance detail section.
 *
 * Covers both author-kind branches (agent + human) and the "recommended
 * in <task>" link.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { StrategyProvenanceSection } from './StrategyProvenanceSection'
import {
  useStrategyProvenance,
  type StrategyProvenance,
} from '@/hooks/useStrategyProvenance'

vi.mock('@/hooks/useStrategyProvenance', () => ({
  useStrategyProvenance: vi.fn(),
}))

const mockedUseStrategyProvenance = vi.mocked(useStrategyProvenance)

function buildProvenance(
  overrides: Partial<StrategyProvenance> = {}
): StrategyProvenance {
  return {
    authorKind: 'human',
    agentLabel: null,
    recommendingTask: null,
    isLoading: false,
    ...overrides,
  }
}

function renderSection(strategyId = 'strat-1'): void {
  render(
    <MemoryRouter>
      <StrategyProvenanceSection
        strategyId={strategyId}
        createdAt="2026-04-15T10:30:00Z"
      />
    </MemoryRouter>
  )
}

beforeEach(() => {
  mockedUseStrategyProvenance.mockReset()
})

describe('StrategyProvenanceSection', () => {
  it('renders the Human author-kind for non-agent strategies', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({ authorKind: 'human' })
    )

    renderSection()

    expect(
      screen.getByTestId('strategy-provenance-section-strat-1')
    ).toBeInTheDocument()
    expect(
      screen.getByTestId('strategy-provenance-author-kind-strat-1')
    ).toHaveTextContent('Human')
    // No API-key-label field shown for human strategies.
    expect(
      screen.queryByTestId('strategy-provenance-key-label-strat-1')
    ).not.toBeInTheDocument()
  })

  it('renders Agent + API-key label for agent-authored strategies', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({
        authorKind: 'agent',
        agentLabel: 'claude-explorer',
      })
    )

    renderSection()

    expect(
      screen.getByTestId('strategy-provenance-author-kind-strat-1')
    ).toHaveTextContent('Agent')
    const labelLink = screen.getByTestId(
      'strategy-provenance-key-label-strat-1'
    ) as HTMLAnchorElement
    expect(labelLink.textContent).toBe('claude-explorer')
    expect(labelLink.getAttribute('href')).toBe(
      '/activity?actor_label=claude-explorer'
    )
  })

  it('renders the recommending-task link when a finding points at this strategy', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({
        authorKind: 'agent',
        agentLabel: 'claude-explorer',
        recommendingTask: {
          taskId: 'task-xyz',
          taskTitle: 'Explore mean-reversion variants',
        },
      })
    )

    renderSection()

    const taskRow = screen.getByTestId('strategy-provenance-task-link-strat-1')
    expect(taskRow.textContent).toContain('Recommended in')
    expect(taskRow.textContent).toContain('Explore mean-reversion variants')

    const taskLink = taskRow.querySelector('a')
    expect(taskLink).toBeTruthy()
    expect(taskLink!.getAttribute('href')).toBe('/exploration-tasks/task-xyz')
  })

  it('omits the recommending-task line when no finding matches', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({
        authorKind: 'human',
        recommendingTask: null,
      })
    )

    renderSection()

    expect(
      screen.queryByTestId('strategy-provenance-task-link-strat-1')
    ).not.toBeInTheDocument()
  })

  it('renders the unlabelled-key fallback when agent label is null', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({
        authorKind: 'agent',
        agentLabel: null,
      })
    )

    renderSection()

    expect(screen.getByText('Unlabelled key')).toBeInTheDocument()
  })

  it('shows a loading hint while author kind is still unknown and loading', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({ authorKind: 'unknown', isLoading: true })
    )

    renderSection()

    expect(
      screen.getByTestId('strategy-provenance-author-kind-strat-1')
    ).toHaveTextContent(/Loading/)
  })
})
