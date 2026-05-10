import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ApiKeyList } from './ApiKeyList'
import type { ApiKeySummary } from '@/services/api/types'

function makeKey(overrides: Partial<ApiKeySummary> = {}): ApiKeySummary {
  return {
    id: '00000000-0000-0000-0000-00000000abcd',
    label: 'claude-code-laptop',
    scopes: ['read', 'trade'],
    created_at: '2024-01-15T00:00:00Z',
    last_used_at: null,
    revoked_at: null,
    expires_at: null,
    is_active: true,
    ...overrides,
  }
}

describe('ApiKeyList', () => {
  it('renders one row per key with label and last 8 of id', () => {
    const items = [
      makeKey({
        id: '00000000-0000-0000-0000-000000000001',
        label: 'first',
      }),
      makeKey({
        id: '00000000-0000-0000-0000-000000000002',
        label: 'second',
      }),
    ]

    render(
      <ApiKeyList items={items} onRevoke={vi.fn()} pendingRevokeId={null} />
    )

    expect(screen.getByText('first')).toBeInTheDocument()
    expect(screen.getByText('second')).toBeInTheDocument()
    // Last 8 chars (hex, no dashes)
    expect(screen.getByText('…00000001')).toBeInTheDocument()
    expect(screen.getByText('…00000002')).toBeInTheDocument()
  })

  it('renders one chip per scope', () => {
    const items = [
      makeKey({
        id: '00000000-0000-0000-0000-000000000001',
        scopes: ['read', 'trade', 'admin'],
      }),
    ]

    render(
      <ApiKeyList items={items} onRevoke={vi.fn()} pendingRevokeId={null} />
    )

    expect(
      screen.getByTestId(
        'api-key-row-scope-00000000-0000-0000-0000-000000000001-read'
      )
    ).toBeInTheDocument()
    expect(
      screen.getByTestId(
        'api-key-row-scope-00000000-0000-0000-0000-000000000001-trade'
      )
    ).toBeInTheDocument()
    expect(
      screen.getByTestId(
        'api-key-row-scope-00000000-0000-0000-0000-000000000001-admin'
      )
    ).toBeInTheDocument()
  })

  it('shows "Never" when last_used_at is null', () => {
    render(
      <ApiKeyList
        items={[makeKey({ last_used_at: null })]}
        onRevoke={vi.fn()}
        pendingRevokeId={null}
      />
    )

    expect(screen.getByText('Never')).toBeInTheDocument()
  })

  it('shows Active status badge for active keys', () => {
    const items = [
      makeKey({
        id: '00000000-0000-0000-0000-000000000001',
        is_active: true,
      }),
    ]

    render(
      <ApiKeyList items={items} onRevoke={vi.fn()} pendingRevokeId={null} />
    )

    const status = screen.getByTestId(
      'api-key-status-00000000-0000-0000-0000-000000000001'
    )
    expect(status).toHaveTextContent('Active')
  })

  it('shows Revoked status and hides revoke button when revoked', () => {
    const items = [
      makeKey({
        id: '00000000-0000-0000-0000-000000000001',
        is_active: false,
        revoked_at: '2024-02-01T00:00:00Z',
      }),
    ]

    render(
      <ApiKeyList items={items} onRevoke={vi.fn()} pendingRevokeId={null} />
    )

    expect(
      screen.getByTestId('api-key-status-00000000-0000-0000-0000-000000000001')
    ).toHaveTextContent('Revoked')
    expect(
      screen.queryByTestId(
        'api-key-revoke-00000000-0000-0000-0000-000000000001-btn'
      )
    ).not.toBeInTheDocument()
  })

  it('shows Expired status when expires_at is in the past', () => {
    const past = new Date(Date.now() - 24 * 60 * 60 * 1000).toISOString()
    const items = [
      makeKey({
        id: '00000000-0000-0000-0000-000000000001',
        is_active: false,
        expires_at: past,
      }),
    ]

    render(
      <ApiKeyList items={items} onRevoke={vi.fn()} pendingRevokeId={null} />
    )

    expect(
      screen.getByTestId('api-key-status-00000000-0000-0000-0000-000000000001')
    ).toHaveTextContent('Expired')
  })

  it('calls onRevoke with the key when the revoke button is clicked', async () => {
    const user = userEvent.setup()
    const onRevoke = vi.fn()
    const key = makeKey({ id: '00000000-0000-0000-0000-000000000001' })

    render(
      <ApiKeyList items={[key]} onRevoke={onRevoke} pendingRevokeId={null} />
    )

    await user.click(
      screen.getByTestId(
        'api-key-revoke-00000000-0000-0000-0000-000000000001-btn'
      )
    )

    expect(onRevoke).toHaveBeenCalledWith(key)
  })

  it('disables and relabels the revoke button while pending', () => {
    const key = makeKey({ id: '00000000-0000-0000-0000-000000000001' })

    render(
      <ApiKeyList
        items={[key]}
        onRevoke={vi.fn()}
        pendingRevokeId="00000000-0000-0000-0000-000000000001"
      />
    )

    const btn = screen.getByTestId(
      'api-key-revoke-00000000-0000-0000-0000-000000000001-btn'
    )
    expect(btn).toBeDisabled()
    expect(btn).toHaveTextContent(/Revoking/i)
  })
})
