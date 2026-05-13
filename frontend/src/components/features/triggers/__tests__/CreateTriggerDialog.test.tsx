/**
 * Tests for CreateTriggerDialog.
 *
 * Mocks at the API-client boundary so the form's validation + submit-shape
 * contract is exercised through the real hooks. We assert on what the user
 * sees + what the backend would receive (the create payload).
 */
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CreateTriggerDialog } from '../CreateTriggerDialog'
import { triggersApi } from '@/services/api/triggers'
import { apiKeysApi } from '@/services/api/apiKeys'
import type { ApiKeyListResponse, TriggerResponse } from '@/services/api/types'

vi.mock('react-hot-toast', () => ({
  default: {
    success: vi.fn(),
    error: vi.fn(),
  },
}))

vi.mock('@/services/api/triggers', () => ({
  triggersApi: {
    listForActivation: vi.fn(),
    getById: vi.fn(),
    create: vi.fn(),
    update: vi.fn(),
    delete: vi.fn(),
    listFires: vi.fn(),
  },
}))

vi.mock('@/services/api/apiKeys', () => ({
  apiKeysApi: {
    list: vi.fn(),
    create: vi.fn(),
    revoke: vi.fn(),
  },
}))

const sampleTrigger: TriggerResponse = {
  id: 'trigger-1',
  activation_id: 'activation-1',
  user_id: 'user-1',
  condition_type: 'DRAWDOWN_THRESHOLD',
  condition_params: {
    threshold_pct: '5',
    lookback_days: 3,
    metric: 'PORTFOLIO_TOTAL',
  },
  agent_prompt: 'Investigate.',
  cooldown_seconds: 3600,
  last_fired_at: null,
  status: 'ACTIVE',
  priority: 0,
  default_api_key_id: null,
  expires_at: null,
  created_at: '2026-05-09T12:00:00Z',
  created_by: 'user-1',
  updated_at: '2026-05-09T12:00:00Z',
  mode: 'direct',
}

const emptyApiKeys: ApiKeyListResponse = { items: [], total: 0 }

function createWrapper(): ({
  children,
}: {
  children: React.ReactNode
}) => React.JSX.Element {
  const client = new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  })
  return ({ children }: { children: React.ReactNode }): React.JSX.Element => (
    <QueryClientProvider client={client}>{children}</QueryClientProvider>
  )
}

beforeEach(() => {
  vi.clearAllMocks()
  vi.mocked(apiKeysApi.list).mockResolvedValue(emptyApiKeys)
})

describe('CreateTriggerDialog', () => {
  it('renders nothing when isOpen is false', () => {
    render(
      <CreateTriggerDialog
        isOpen={false}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )
    expect(
      screen.queryByTestId('trigger-create-dialog')
    ).not.toBeInTheDocument()
  })

  it('renders the dialog with default DRAWDOWN_THRESHOLD params visible', () => {
    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )
    expect(screen.getByTestId('trigger-create-dialog')).toBeInTheDocument()
    expect(
      screen.getByTestId('trigger-create-drawdown-params')
    ).toBeInTheDocument()
    expect(screen.getByTestId('trigger-create-threshold-pct')).toHaveValue(5)
    expect(screen.getByTestId('trigger-create-lookback-days')).toHaveValue(3)
  })

  it('reveals VOLATILITY_SPIKE params when the type is changed', async () => {
    const user = userEvent.setup()
    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )
    await user.selectOptions(
      screen.getByTestId('trigger-create-condition-type'),
      'VOLATILITY_SPIKE'
    )
    expect(
      screen.getByTestId('trigger-create-volatility-params')
    ).toBeInTheDocument()
    expect(screen.getByTestId('trigger-create-over-days')).toBeInTheDocument()
  })

  it('reveals EARNINGS_PROXIMITY params when the type is changed', async () => {
    const user = userEvent.setup()
    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )
    await user.selectOptions(
      screen.getByTestId('trigger-create-condition-type'),
      'EARNINGS_PROXIMITY'
    )
    expect(
      screen.getByTestId('trigger-create-earnings-params')
    ).toBeInTheDocument()
    expect(screen.getByTestId('trigger-create-days-before')).toBeInTheDocument()
  })

  it('rejects an empty agent prompt with a validation error', async () => {
    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    // fireEvent.submit on the form bypasses any quirks around clicking a
    // submit button inside a `dialog`-styled overlay in JSDOM.
    fireEvent.submit(screen.getByTestId('trigger-create-form'))

    expect(
      await screen.findByTestId('trigger-create-agent-prompt-error')
    ).toHaveTextContent(/Agent prompt is required/i)
    expect(triggersApi.create).not.toHaveBeenCalled()
  })

  it('rejects an out-of-range drawdown threshold', async () => {
    const user = userEvent.setup()
    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    // Clear and set an out-of-range value (200 > 100 limit).
    const thresholdInput = screen.getByTestId('trigger-create-threshold-pct')
    await user.clear(thresholdInput)
    await user.type(thresholdInput, '200')
    await user.type(
      screen.getByTestId('trigger-create-agent-prompt'),
      'Investigate.'
    )
    fireEvent.submit(screen.getByTestId('trigger-create-form'))

    expect(
      await screen.findByTestId('trigger-create-threshold-pct-error')
    ).toHaveTextContent(/Threshold must be in/i)
    expect(triggersApi.create).not.toHaveBeenCalled()
  })

  it('submits a DRAWDOWN_THRESHOLD trigger with the expected payload', async () => {
    vi.mocked(triggersApi.create).mockResolvedValueOnce(sampleTrigger)
    const onClose = vi.fn()
    const user = userEvent.setup()

    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={onClose}
      />,
      { wrapper: createWrapper() }
    )

    await user.type(
      screen.getByTestId('trigger-create-agent-prompt'),
      'Investigate the drawdown.'
    )
    // Default cooldown = 1 hour → 3600 seconds. Keep defaults.
    fireEvent.submit(screen.getByTestId('trigger-create-form'))

    await waitFor(() => {
      expect(triggersApi.create).toHaveBeenCalledWith('activation-1', {
        condition_type: 'DRAWDOWN_THRESHOLD',
        condition_params: {
          threshold_pct: '5',
          lookback_days: 3,
          metric: 'PORTFOLIO_TOTAL',
        },
        agent_prompt: 'Investigate the drawdown.',
        cooldown_seconds: 3600,
        mode: 'direct',
      })
    })
    await waitFor(() => expect(onClose).toHaveBeenCalled())
  })

  it('renders the invocation-mode radio with DIRECT as the default', async () => {
    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    // Both radio inputs render; DIRECT is checked by default.
    const direct = screen.getByTestId(
      'trigger-create-mode-direct'
    ) as HTMLInputElement
    const queue = screen.getByTestId(
      'trigger-create-mode-queue'
    ) as HTMLInputElement
    expect(direct.checked).toBe(true)
    expect(queue.checked).toBe(false)
  })

  it('submits mode=queue when the queue radio is selected', async () => {
    vi.mocked(triggersApi.create).mockResolvedValueOnce(sampleTrigger)
    const user = userEvent.setup()

    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    await user.type(
      screen.getByTestId('trigger-create-agent-prompt'),
      'Use desktop tools to investigate this fire.'
    )
    await user.click(screen.getByTestId('trigger-create-mode-queue'))
    fireEvent.submit(screen.getByTestId('trigger-create-form'))

    await waitFor(() => {
      expect(triggersApi.create).toHaveBeenCalledWith(
        'activation-1',
        expect.objectContaining({
          mode: 'queue',
        })
      )
    })
  })

  it('submits via a real button click without tripping HTML5 step validation', async () => {
    // Regression for issue #269: previously the threshold-pct input had
    // `min="0.01" step="0.1"` while the default value `5` did not sit on
    // the resulting step grid `(value - min) % step !== 0`. Chromium
    // blocked form submission at the constraint-validation layer and the
    // `onSubmit` handler never ran — so the trigger row never appeared
    // in the E2E. `fireEvent.submit` masks this in JSDOM because it
    // dispatches the submit event directly; we now exercise the button
    // click path to keep the constraint check exercised.
    vi.mocked(triggersApi.create).mockResolvedValueOnce(sampleTrigger)
    const user = userEvent.setup()

    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    await user.type(
      screen.getByTestId('trigger-create-agent-prompt'),
      'Investigate the drawdown.'
    )
    // Real-button click — this is the path the E2E uses, and the one
    // that runs HTML5 constraint validation.
    await user.click(screen.getByTestId('trigger-create-submit-btn'))

    await waitFor(() => {
      expect(triggersApi.create).toHaveBeenCalledWith(
        'activation-1',
        expect.objectContaining({
          condition_type: 'DRAWDOWN_THRESHOLD',
          agent_prompt: 'Investigate the drawdown.',
        })
      )
    })
  })

  it('translates cooldown unit changes correctly (days)', async () => {
    vi.mocked(triggersApi.create).mockResolvedValueOnce(sampleTrigger)
    const user = userEvent.setup()

    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    const cooldownValue = screen.getByTestId('trigger-create-cooldown-value')
    await user.clear(cooldownValue)
    await user.type(cooldownValue, '2')
    await user.selectOptions(
      screen.getByTestId('trigger-create-cooldown-unit'),
      'days'
    )
    await user.type(
      screen.getByTestId('trigger-create-agent-prompt'),
      'Investigate.'
    )
    fireEvent.submit(screen.getByTestId('trigger-create-form'))

    await waitFor(() => {
      expect(triggersApi.create).toHaveBeenCalledWith(
        'activation-1',
        expect.objectContaining({
          cooldown_seconds: 2 * 86_400,
        })
      )
    })
  })

  it('shows the API key picker only when the user has more than one trade key', async () => {
    vi.mocked(apiKeysApi.list).mockResolvedValueOnce({
      items: [
        {
          id: 'key-1',
          label: 'laptop-agent',
          scopes: ['trade'],
          created_at: '2026-04-01T00:00:00Z',
          last_used_at: null,
          revoked_at: null,
          expires_at: null,
          is_active: true,
        },
        {
          id: 'key-2',
          label: 'scheduled-runner',
          scopes: ['trade'],
          created_at: '2026-04-02T00:00:00Z',
          last_used_at: null,
          revoked_at: null,
          expires_at: null,
          is_active: true,
        },
      ],
      total: 2,
    })

    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    await waitFor(() => {
      expect(
        screen.getByTestId('trigger-create-default-api-key')
      ).toBeInTheDocument()
    })
  })

  it('does not show the API key picker when the user has only one usable key', async () => {
    vi.mocked(apiKeysApi.list).mockResolvedValueOnce({
      items: [
        {
          id: 'key-1',
          label: 'laptop-agent',
          scopes: ['trade'],
          created_at: '2026-04-01T00:00:00Z',
          last_used_at: null,
          revoked_at: null,
          expires_at: null,
          is_active: true,
        },
      ],
      total: 1,
    })

    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )

    // Give the query a tick to settle; assert the picker stays hidden.
    await waitFor(() => {
      expect(screen.getByTestId('trigger-create-dialog')).toBeInTheDocument()
    })
    expect(
      screen.queryByTestId('trigger-create-default-api-key')
    ).not.toBeInTheDocument()
  })

  it('disables the CUSTOM_RULE option per Phase F Q1', () => {
    render(
      <CreateTriggerDialog
        isOpen={true}
        activationId="activation-1"
        onClose={() => {}}
      />,
      { wrapper: createWrapper() }
    )
    const select = screen.getByTestId(
      'trigger-create-condition-type'
    ) as HTMLSelectElement
    const customOption = Array.from(select.options).find(
      (opt) => opt.value === 'CUSTOM_RULE'
    )
    expect(customOption).toBeDefined()
    expect(customOption?.disabled).toBe(true)
  })
})
