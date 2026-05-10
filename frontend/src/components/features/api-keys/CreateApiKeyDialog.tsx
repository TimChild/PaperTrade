/**
 * Create API Key dialog — two-stage flow.
 *
 * Stage 1: form (label, scopes, optional expiry).
 * Stage 2: mint result (raw key shown once, with copy button).
 *
 * Stage transition is driven by the parent passing `mintResult` as a prop
 * once the mutation resolves. The dialog does not sync internal state
 * from props with `useEffect` — the parent re-mounts the form portion via
 * the `formKey` strategy if it ever needs to reset mid-session.
 */
import { useState } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import type { ApiKeyScope, CreateApiKeyResponse } from '@/services/api/types'

interface CreateApiKeyDialogProps {
  isOpen: boolean
  onClose: () => void
  onSubmit: (data: {
    label: string
    scopes: ApiKeyScope[]
    expiresAt: string | null
  }) => void
  isPending: boolean
  /**
   * Set to the mint response once the mutation succeeds. Triggers the
   * "save your key" stage of the dialog. `null` while the form is active.
   */
  mintResult: CreateApiKeyResponse | null
  /** Called when the user dismisses the success view. */
  onDone: () => void
}

const ALL_SCOPES: { value: ApiKeyScope; description: string }[] = [
  { value: 'read', description: 'List and read your data' },
  { value: 'trade', description: 'Execute trades, deposits, withdrawals' },
  { value: 'admin', description: 'Backfill snapshots, refresh prices' },
]
const DEFAULT_SCOPES: ApiKeyScope[] = ['read', 'trade']
const LABEL_MAX = 64

export function CreateApiKeyDialog({
  isOpen,
  onClose,
  onSubmit,
  isPending,
  mintResult,
  onDone,
}: CreateApiKeyDialogProps): React.JSX.Element | null {
  if (!isOpen) return null

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
      data-testid="api-key-create-backdrop"
      role="dialog"
      aria-modal="true"
      aria-labelledby="api-key-create-title"
    >
      <div className="w-full max-w-md rounded-lg bg-white shadow-xl dark:bg-gray-800">
        {mintResult === null ? (
          <CreateApiKeyForm
            onClose={onClose}
            onSubmit={onSubmit}
            isPending={isPending}
          />
        ) : (
          <CreateApiKeyResult mintResult={mintResult} onDone={onDone} />
        )}
      </div>
    </div>
  )
}

interface FormStageProps {
  onClose: () => void
  onSubmit: (data: {
    label: string
    scopes: ApiKeyScope[]
    expiresAt: string | null
  }) => void
  isPending: boolean
}

function CreateApiKeyForm({
  onClose,
  onSubmit,
  isPending,
}: FormStageProps): React.JSX.Element {
  const [label, setLabel] = useState('')
  const [scopes, setScopes] = useState<ApiKeyScope[]>(DEFAULT_SCOPES)
  const [expiresAt, setExpiresAt] = useState('')
  const [errors, setErrors] = useState<Record<string, string>>({})

  const toggleScope = (scope: ApiKeyScope): void => {
    setScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    )
  }

  const validate = (): boolean => {
    const next: Record<string, string> = {}
    const trimmed = label.trim()
    if (!trimmed) {
      next.label = 'Label is required'
    } else if (trimmed.length > LABEL_MAX) {
      next.label = `Label must be ${LABEL_MAX} characters or fewer`
    }
    if (scopes.length === 0) {
      next.scopes = 'Select at least one scope'
    }
    setErrors(next)
    return Object.keys(next).length === 0
  }

  const handleSubmit = (e: React.FormEvent): void => {
    e.preventDefault()
    if (!validate()) return
    onSubmit({
      label: label.trim(),
      scopes,
      // Convert YYYY-MM-DD to end-of-day UTC ISO string so the key is
      // valid through the entire chosen day.
      expiresAt: expiresAt
        ? new Date(`${expiresAt}T23:59:59.000Z`).toISOString()
        : null,
    })
  }

  return (
    <form
      onSubmit={handleSubmit}
      data-testid="api-key-create-form"
      className="space-y-4 p-6"
    >
      <div>
        <h2
          id="api-key-create-title"
          className="text-lg font-semibold text-gray-900 dark:text-white"
        >
          New API key
        </h2>
        <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
          Create a key for an MCP server, script, or scheduled agent. The secret
          will be shown once — store it securely.
        </p>
      </div>

      {/* Label */}
      <div className="space-y-1">
        <Label htmlFor="api-key-label">Label</Label>
        <Input
          id="api-key-label"
          data-testid="api-key-create-label-input"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="claude-code-laptop"
          maxLength={LABEL_MAX}
          autoFocus
        />
        {errors.label !== undefined && (
          <p
            data-testid="api-key-create-label-error"
            className="text-sm text-red-600 dark:text-red-400"
          >
            {errors.label}
          </p>
        )}
      </div>

      {/* Scopes */}
      <fieldset className="space-y-2">
        <legend className="text-sm font-medium text-foreground-primary">
          Scopes
        </legend>
        <div className="space-y-2 rounded-input border border-gray-300 p-3 dark:border-gray-700">
          {ALL_SCOPES.map(({ value, description }) => {
            const checked = scopes.includes(value)
            return (
              <label
                key={value}
                className="flex cursor-pointer items-start gap-3 rounded-input p-1 hover:bg-gray-50 dark:hover:bg-gray-900"
              >
                <input
                  type="checkbox"
                  data-testid={`api-key-create-scope-${value}`}
                  checked={checked}
                  onChange={() => toggleScope(value)}
                  className="mt-1 h-4 w-4 rounded border-gray-300 text-primary"
                />
                <div className="flex flex-col">
                  <span className="font-mono text-sm font-medium text-gray-900 dark:text-white">
                    {value}
                  </span>
                  <span className="text-xs text-gray-500 dark:text-gray-400">
                    {description}
                  </span>
                </div>
              </label>
            )
          })}
        </div>
        {errors.scopes !== undefined && (
          <p
            data-testid="api-key-create-scopes-error"
            className="text-sm text-red-600 dark:text-red-400"
          >
            {errors.scopes}
          </p>
        )}
      </fieldset>

      {/* Optional expiry */}
      <div className="space-y-1">
        <Label htmlFor="api-key-expires">
          Expires{' '}
          <span className="text-xs text-gray-500">
            (optional — never expires if blank)
          </span>
        </Label>
        <Input
          id="api-key-expires"
          data-testid="api-key-create-expires-input"
          type="date"
          value={expiresAt}
          onChange={(e) => setExpiresAt(e.target.value)}
        />
      </div>

      {/* Actions */}
      <div className="flex justify-end gap-2 pt-2">
        <Button
          type="button"
          variant="secondary"
          onClick={onClose}
          disabled={isPending}
          data-testid="api-key-create-cancel-btn"
        >
          Cancel
        </Button>
        <Button
          type="submit"
          disabled={isPending}
          data-testid="api-key-create-submit-btn"
        >
          {isPending ? 'Creating…' : 'Create key'}
        </Button>
      </div>
    </form>
  )
}

interface ResultStageProps {
  mintResult: CreateApiKeyResponse
  onDone: () => void
}

function CreateApiKeyResult({
  mintResult,
  onDone,
}: ResultStageProps): React.JSX.Element {
  const [copied, setCopied] = useState(false)

  const handleCopy = (): void => {
    void navigator.clipboard.writeText(mintResult.raw_key).then(() => {
      setCopied(true)
      // Visible feedback that resets after 1.5s. setTimeout here rather
      // than useEffect — this is an event-driven side-effect, not a
      // synchronization with an external system.
      window.setTimeout(() => {
        setCopied(false)
      }, 1500)
    })
  }

  return (
    <div className="space-y-4 p-6" data-testid="api-key-mint-result">
      <div>
        <h2
          id="api-key-create-title"
          className="text-lg font-semibold text-gray-900 dark:text-white"
        >
          Save your API key
        </h2>
        <p className="mt-1 text-sm text-red-600 dark:text-red-400">
          This is the only time you will see this secret. Copy it now and store
          it somewhere safe — anyone with this key can act as your machine
          identity.
        </p>
      </div>

      <div className="space-y-1">
        <Label htmlFor="api-key-mint-result-value">Secret</Label>
        <div
          id="api-key-mint-result-value"
          data-testid="api-key-mint-result-value"
          className="break-all rounded-input border border-gray-300 bg-gray-50 p-3 font-mono text-sm tracking-tight text-gray-900 dark:border-gray-700 dark:bg-gray-900 dark:text-gray-100"
          role="textbox"
          aria-readonly="true"
        >
          {mintResult.raw_key}
        </div>
      </div>

      <dl className="grid grid-cols-3 gap-2 text-xs">
        <div>
          <dt className="text-gray-500 dark:text-gray-400">Label</dt>
          <dd
            data-testid="api-key-mint-result-label"
            className="mt-0.5 font-medium text-gray-900 dark:text-white"
          >
            {mintResult.label}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500 dark:text-gray-400">Scopes</dt>
          <dd
            data-testid="api-key-mint-result-scopes"
            className="mt-0.5 font-mono text-gray-900 dark:text-white"
          >
            {mintResult.scopes.join(', ')}
          </dd>
        </div>
        <div>
          <dt className="text-gray-500 dark:text-gray-400">Expires</dt>
          <dd
            data-testid="api-key-mint-result-expires"
            className="mt-0.5 text-gray-900 dark:text-white"
          >
            {mintResult.expires_at !== null
              ? new Date(mintResult.expires_at).toLocaleDateString()
              : 'Never'}
          </dd>
        </div>
      </dl>

      <div className="flex justify-end gap-2 pt-2">
        <Button
          type="button"
          variant="secondary"
          onClick={handleCopy}
          data-testid="api-key-mint-result-copy-btn"
        >
          {copied ? 'Copied!' : 'Copy secret'}
        </Button>
        <Button
          type="button"
          onClick={onDone}
          data-testid="api-key-mint-result-done-btn"
        >
          Done
        </Button>
      </div>
    </div>
  )
}
