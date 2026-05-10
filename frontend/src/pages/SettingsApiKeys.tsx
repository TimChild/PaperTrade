/**
 * Settings → API Keys page (Phase H3).
 *
 * Replaces the JWT-from-browser-console + curl workflow that agents and
 * MCP servers had to use during Phase B/C. The user can mint, list, and
 * revoke API keys here.
 *
 * Mint flow has two stages handled by `<CreateApiKeyDialog>`:
 *   1. Form: label / scopes / optional expiry.
 *   2. Result: raw key shown once with a copy button, then the user
 *      acknowledges and the dialog closes.
 *
 * The raw key is held only in this component's state, never persisted
 * anywhere client-side. Closing the dialog clears it.
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { ConfirmDialog } from '@/components/ui/ConfirmDialog'
import { EmptyState } from '@/components/ui/EmptyState'
import { LoadingSpinner } from '@/components/ui/LoadingSpinner'
import { ApiKeyList } from '@/components/features/api-keys/ApiKeyList'
import { CreateApiKeyDialog } from '@/components/features/api-keys/CreateApiKeyDialog'
import {
  useApiKeys,
  useCreateApiKey,
  useRevokeApiKey,
} from '@/hooks/useApiKeys'
import type {
  ApiKeyScope,
  ApiKeySummary,
  CreateApiKeyResponse,
} from '@/services/api/types'
import toast from 'react-hot-toast'

export function SettingsApiKeys(): React.JSX.Element {
  const [showCreate, setShowCreate] = useState(false)
  const [mintResult, setMintResult] = useState<CreateApiKeyResponse | null>(
    null
  )
  const [revokeTarget, setRevokeTarget] = useState<ApiKeySummary | null>(null)

  const { data: list, isLoading, error } = useApiKeys()
  const createApiKey = useCreateApiKey()
  const revokeApiKey = useRevokeApiKey()

  const items = list?.items ?? []

  const openCreate = (): void => {
    setMintResult(null)
    setShowCreate(true)
  }

  const closeCreate = (): void => {
    setShowCreate(false)
    setMintResult(null)
  }

  const handleSubmit = (data: {
    label: string
    scopes: ApiKeyScope[]
    expiresAt: string | null
  }): void => {
    createApiKey.mutate(
      {
        label: data.label,
        scopes: data.scopes,
        expires_at: data.expiresAt,
      },
      {
        onSuccess: (response) => {
          setMintResult(response)
          toast.success('API key created. Copy it now.')
        },
        onError: () => {
          toast.error('Failed to create API key')
        },
      }
    )
  }

  const handleRevokeConfirm = (): void => {
    if (revokeTarget === null) return
    const target = revokeTarget
    revokeApiKey.mutate(target.id, {
      onSuccess: () => {
        toast.success(`Revoked "${target.label}"`)
        setRevokeTarget(null)
      },
      onError: () => {
        toast.error('Failed to revoke API key')
      },
    })
  }

  return (
    <div className="space-y-6" data-testid="settings-api-keys-page">
      <header className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <p className="text-xs uppercase tracking-widest text-gray-500 dark:text-gray-400">
            Settings
          </p>
          <h1 className="mt-1 text-2xl font-bold text-gray-900 dark:text-white">
            API keys
          </h1>
          <p className="mt-2 max-w-prose text-sm text-gray-500 dark:text-gray-400">
            API keys let you authenticate from MCP servers, scripts, or
            scheduled agents. Each key acts as your machine identity — keep them
            secret. Pair the key with{' '}
            <code className="rounded bg-gray-100 px-1 py-0.5 font-mono text-xs dark:bg-gray-800">
              Authorization: ApiKey &lt;key&gt;
            </code>{' '}
            or{' '}
            <code className="rounded bg-gray-100 px-1 py-0.5 font-mono text-xs dark:bg-gray-800">
              X-API-Key
            </code>
            .
          </p>
        </div>
        <Button
          onClick={openCreate}
          data-testid="api-key-create-btn"
          disabled={isLoading}
        >
          New key
        </Button>
      </header>

      {isLoading && (
        <div data-testid="api-keys-loading" className="py-12">
          <LoadingSpinner size="lg" />
        </div>
      )}

      {error && !isLoading && (
        <div
          data-testid="api-keys-error"
          className="rounded-lg border border-red-200 bg-red-50 p-6 text-center dark:border-red-800 dark:bg-red-900/20"
        >
          <p className="text-red-600 dark:text-red-400">
            Failed to load API keys. Please try again.
          </p>
        </div>
      )}

      {!isLoading && !error && items.length === 0 && (
        <EmptyState
          message="No API keys yet. Create one to authenticate an agent or MCP server."
          action={
            <Button onClick={openCreate} data-testid="api-key-empty-create-btn">
              Create your first key
            </Button>
          }
        />
      )}

      {!isLoading && !error && items.length > 0 && (
        <ApiKeyList
          items={items}
          onRevoke={(apiKey) => setRevokeTarget(apiKey)}
          pendingRevokeId={
            revokeApiKey.isPending ? (revokeTarget?.id ?? null) : null
          }
        />
      )}

      {/* Create + show-once mint dialog */}
      <CreateApiKeyDialog
        isOpen={showCreate}
        onClose={closeCreate}
        onSubmit={handleSubmit}
        isPending={createApiKey.isPending}
        mintResult={mintResult}
        onDone={closeCreate}
      />

      {/* Revoke confirmation */}
      <ConfirmDialog
        isOpen={revokeTarget !== null}
        title="Revoke API key"
        message={
          revokeTarget !== null
            ? `Revoke "${revokeTarget.label}"? This will immediately invalidate any session using this key.`
            : ''
        }
        confirmLabel="Revoke"
        variant="danger"
        onConfirm={handleRevokeConfirm}
        onCancel={() => setRevokeTarget(null)}
        isLoading={revokeApiKey.isPending}
      />
    </div>
  )
}

