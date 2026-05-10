/**
 * Helpers for deriving an exploration task's "headline" from its prompt.
 *
 * The backend has no separate `title` column on `ExplorationTask` —
 * everything lives in the free-form `prompt`. The H1 dashboard surfaces a
 * one-line headline for list rows and detail eyebrows, so we extract the
 * first non-empty paragraph and clip it. The create form folds an
 * optional title into the prompt as a leading line, so this strategy
 * recovers it cleanly.
 */

const MAX_TITLE_LENGTH = 120

/**
 * Extract a short headline from an exploration task prompt.
 *
 * Strategy:
 *
 * 1. Take the first non-empty line.
 * 2. Strip a leading markdown heading marker ("# ", "## ", ...).
 * 3. If the line is longer than `MAX_TITLE_LENGTH`, truncate at the last
 *    space before the cap and append a single ellipsis.
 *
 * Returns "Untitled task" only as a defensive fallback for an empty
 * prompt — the entity invariant rejects empty prompts on the backend, so
 * this branch should never fire under normal flow.
 */
export function extractTaskTitle(prompt: string): string {
  const firstLine = prompt
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.length > 0)

  if (!firstLine) {
    return 'Untitled task'
  }

  // Strip leading markdown heading markers (# / ## / ###) plus their space.
  const stripped = firstLine.replace(/^#{1,6}\s+/, '').trim()

  if (stripped.length <= MAX_TITLE_LENGTH) {
    return stripped
  }

  const truncated = stripped.slice(0, MAX_TITLE_LENGTH)
  const lastSpace = truncated.lastIndexOf(' ')
  // Only break at a space if it lands far enough in to keep the title
  // readable; otherwise just hard-truncate at the cap.
  const cut = lastSpace > MAX_TITLE_LENGTH * 0.5 ? lastSpace : MAX_TITLE_LENGTH
  return `${stripped.slice(0, cut).trimEnd()}…`
}

/**
 * The remainder of the prompt after the headline line — i.e. the
 * "body" agents are meant to read in detail. Returns an empty string
 * when the prompt is a single line.
 */
export function extractTaskBody(prompt: string): string {
  const lines = prompt.split('\n')
  const firstNonEmptyIndex = lines.findIndex((line) => line.trim().length > 0)
  if (firstNonEmptyIndex === -1) {
    return ''
  }
  // Skip past the headline and any blank lines immediately after it so the
  // body reads cleanly.
  let i = firstNonEmptyIndex + 1
  while (i < lines.length && lines[i].trim().length === 0) {
    i += 1
  }
  return lines.slice(i).join('\n').trim()
}
