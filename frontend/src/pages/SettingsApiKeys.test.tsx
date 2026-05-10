import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { http, HttpResponse } from 'msw'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter } from 'react-router-dom'
import { server } from '../../tests/setup'
import { SettingsApiKeys } from './SettingsApiKeys'
import type {
  ApiKeyListResponse,
  ApiKeySummary,
  CreateApiKeyResponse,
} from '@/services/api/types'

const API_BASE_URL = 'http://localhost:8000/api/v1'

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

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

function renderPage(): void {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  })
  render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter>
        <SettingsApiKeys />
      </MemoryRouter>
    </QueryClientProvider>
  )
}

describe('SettingsApiKeys', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  afterEach(() => {
    server.resetHandlers()
  })

  it('renders the empty state when the user has no keys', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({ items: [], total: 0 })
      )
    )

    renderPage()

    expect(await screen.findByText(/no api keys yet/i)).toBeInTheDocument()
    expect(screen.getByTestId('api-key-empty-create-btn')).toBeInTheDocument()
  })

  it('renders one row per key when the user has keys', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({
          items: [
            makeKey({
              id: '00000000-0000-0000-0000-000000000001',
              label: 'first',
            }),
            makeKey({
              id: '00000000-0000-0000-0000-000000000002',
              label: 'second',
            }),
          ],
          total: 2,
        })
      )
    )

    renderPage()

    expect(
      await screen.findByTestId(
        'api-key-list-row-00000000-0000-0000-0000-000000000001'
      )
    ).toBeInTheDocument()
    expect(
      screen.getByTestId(
        'api-key-list-row-00000000-0000-0000-0000-000000000002'
      )
    ).toBeInTheDocument()
  })

  it('shows the page header with description copy', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({ items: [], total: 0 })
      )
    )

    renderPage()

    expect(
      await screen.findByRole('heading', { name: /api keys/i })
    ).toBeInTheDocument()
    expect(
      screen.getByText(
        /API keys let you authenticate from MCP servers, scripts, or scheduled agents/i
      )
    ).toBeInTheDocument()
  })

  it('mints a key and shows the raw secret on success', async () => {
    let mintCalledWith: unknown = null

    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({ items: [], total: 0 })
      ),
      http.post(`${API_BASE_URL}/api-keys`, async ({ request }) => {
        mintCalledWith = await request.json()
        return HttpResponse.json<CreateApiKeyResponse>({
          id: '00000000-0000-0000-0000-00000000feed',
          label: 'newbot',
          scopes: ['read', 'trade'],
          raw_key: 'zk_minted_secret_value',
          created_at: '2024-02-01T00:00:00Z',
          expires_at: null,
        })
      })
    )

    const user = userEvent.setup()
    renderPage()

    // Wait for the page to load and click "New key"
    await user.click(await screen.findByTestId('api-key-create-btn'))

    // Form opens
    await user.type(screen.getByTestId('api-key-create-label-input'), 'newbot')
    await user.click(screen.getByTestId('api-key-create-submit-btn'))

    // Mint result view appears
    await waitFor(() => {
      expect(screen.getByTestId('api-key-mint-result')).toBeInTheDocument()
    })
    expect(screen.getByTestId('api-key-mint-result-value')).toHaveTextContent(
      'zk_minted_secret_value'
    )
    expect(mintCalledWith).toEqual({
      label: 'newbot',
      scopes: ['read', 'trade'],
      expires_at: null,
    })
  })

  it('clears the mint result when the user clicks Done', async () => {
    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({ items: [], total: 0 })
      ),
      http.post(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<CreateApiKeyResponse>({
          id: '00000000-0000-0000-0000-00000000feed',
          label: 'newbot',
          scopes: ['read'],
          raw_key: 'zk_minted',
          created_at: '2024-02-01T00:00:00Z',
          expires_at: null,
        })
      )
    )

    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByTestId('api-key-create-btn'))
    await user.type(screen.getByTestId('api-key-create-label-input'), 'newbot')
    await user.click(screen.getByTestId('api-key-create-submit-btn'))

    await waitFor(() => {
      expect(screen.getByTestId('api-key-mint-result')).toBeInTheDocument()
    })

    await user.click(screen.getByTestId('api-key-mint-result-done-btn'))

    await waitFor(() => {
      expect(
        screen.queryByTestId('api-key-mint-result')
      ).not.toBeInTheDocument()
    })
  })

  it('opens a confirmation dialog before revoking', async () => {
    const key = makeKey({ id: '00000000-0000-0000-0000-000000000001' })

    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({ items: [key], total: 1 })
      )
    )

    const user = userEvent.setup()
    renderPage()

    await user.click(
      await screen.findByTestId(
        'api-key-revoke-00000000-0000-0000-0000-000000000001-btn'
      )
    )

    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
    expect(
      screen.getByText(/Revoke "claude-code-laptop"\?/)
    ).toBeInTheDocument()
    expect(
      screen.getByText(/immediately invalidate any session using this key/i)
    ).toBeInTheDocument()
  })

  it('cancels revoke without calling the API', async () => {
    const key = makeKey({ id: '00000000-0000-0000-0000-000000000001' })
    const deleteHandler = vi.fn(() => new HttpResponse(null, { status: 204 }))

    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({ items: [key], total: 1 })
      ),
      http.delete(`${API_BASE_URL}/api-keys/:id`, deleteHandler)
    )

    const user = userEvent.setup()
    renderPage()

    await user.click(
      await screen.findByTestId(
        'api-key-revoke-00000000-0000-0000-0000-000000000001-btn'
      )
    )
    await user.click(screen.getByTestId('confirm-dialog-cancel'))

    expect(deleteHandler).not.toHaveBeenCalled()
    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument()
  })

  it('revokes the key when confirmation is accepted', async () => {
    const key = makeKey({ id: '00000000-0000-0000-0000-000000000001' })
    let revokeUrl: string | null = null

    server.use(
      http.get(`${API_BASE_URL}/api-keys`, () =>
        HttpResponse.json<ApiKeyListResponse>({ items: [key], total: 1 })
      ),
      http.delete(`${API_BASE_URL}/api-keys/:id`, ({ request }) => {
        revokeUrl = request.url
        return new HttpResponse(null, { status: 204 })
      })
    )

    const user = userEvent.setup()
    renderPage()

    await user.click(
      await screen.findByTestId(
        'api-key-revoke-00000000-0000-0000-0000-000000000001-btn'
      )
    )
    await user.click(screen.getByTestId('confirm-dialog-confirm'))

    await waitFor(() => {
      expect(revokeUrl).toContain(
        '/api-keys/00000000-0000-0000-0000-000000000001'
      )
    })
  })
})
