/**
 * Tests for the strategy provenance chip.
 *
 * The chip surfaces "Authored by <label>" only for agent-authored
 * strategies. We mock the hook directly so we don't have to wire up the
 * full activity / exploration-tasks query plumbing for every case.
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { StrategyProvenanceChip } from './StrategyProvenanceChip'
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

function renderChip(strategyId = 'strat-1'): void {
  render(
    <MemoryRouter>
      <StrategyProvenanceChip strategyId={strategyId} />
    </MemoryRouter>
  )
}

beforeEach(() => {
  mockedUseStrategyProvenance.mockReset()
})

describe('StrategyProvenanceChip', () => {
  it('renders the agent label for agent-authored strategies', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({
        authorKind: 'agent',
        agentLabel: 'claude-laptop-explorer',
      })
    )

    renderChip()

    expect(
      screen.getByTestId('strategy-provenance-strat-1')
    ).toBeInTheDocument()
    expect(screen.getByText('Authored by')).toBeInTheDocument()
    expect(screen.getByText('claude-laptop-explorer')).toBeInTheDocument()
  })

  it('renders the agent label as a link to the activity drill-down', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({
        authorKind: 'agent',
        agentLabel: 'claude-laptop-explorer',
      })
    )

    renderChip()

    const link = screen.getByTestId(
      'strategy-provenance-actor-link-strat-1'
    ) as HTMLAnchorElement
    expect(link).toBeInTheDocument()
    expect(link.getAttribute('href')).toBe(
      '/activity?actor_label=claude-laptop-explorer'
    )
  })

  it('returns null for human-authored strategies', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({ authorKind: 'human' })
    )

    renderChip()

    expect(
      screen.queryByTestId('strategy-provenance-strat-1')
    ).not.toBeInTheDocument()
  })

  it('returns null while provenance is loading', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({ authorKind: 'unknown', isLoading: true })
    )

    renderChip()

    expect(
      screen.queryByTestId('strategy-provenance-strat-1')
    ).not.toBeInTheDocument()
  })

  it('returns null when author kind is unknown (no matching event)', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({ authorKind: 'unknown', isLoading: false })
    )

    renderChip()

    expect(
      screen.queryByTestId('strategy-provenance-strat-1')
    ).not.toBeInTheDocument()
  })

  it('renders a plain span when agent label is null but kind is agent', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({ authorKind: 'agent', agentLabel: null })
    )

    renderChip()

    expect(screen.getByText('an agent')).toBeInTheDocument()
    // No clickable link in this case.
    expect(
      screen.queryByTestId('strategy-provenance-actor-link-strat-1')
    ).not.toBeInTheDocument()
  })

  it('url-encodes labels with special characters', () => {
    mockedUseStrategyProvenance.mockReturnValue(
      buildProvenance({
        authorKind: 'agent',
        agentLabel: 'claude code/dev',
      })
    )

    renderChip()

    const link = screen.getByTestId(
      'strategy-provenance-actor-link-strat-1'
    ) as HTMLAnchorElement
    expect(link.getAttribute('href')).toBe(
      '/activity?actor_label=claude%20code%2Fdev'
    )
  })
})
