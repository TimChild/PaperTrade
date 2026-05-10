import { describe, it, expect } from 'vitest'
import { extractTaskBody, extractTaskTitle } from './explorationTaskTitle'

describe('extractTaskTitle', () => {
  it('returns the first non-empty line', () => {
    expect(extractTaskTitle('Hello world')).toBe('Hello world')
  })

  it('skips leading blank lines', () => {
    expect(extractTaskTitle('\n\n  \nHello world')).toBe('Hello world')
  })

  it('strips a leading markdown heading marker', () => {
    expect(extractTaskTitle('# Heading')).toBe('Heading')
    expect(extractTaskTitle('## Subheading')).toBe('Subheading')
    expect(extractTaskTitle('### Third')).toBe('Third')
  })

  it('truncates very long lines with an ellipsis', () => {
    const long = 'A'.repeat(140)
    const out = extractTaskTitle(long)
    expect(out.length).toBeLessThan(long.length)
    expect(out.endsWith('…')).toBe(true)
  })

  it('returns "Untitled task" for an empty prompt', () => {
    expect(extractTaskTitle('')).toBe('Untitled task')
    expect(extractTaskTitle('   \n\n   ')).toBe('Untitled task')
  })
})

describe('extractTaskBody', () => {
  it('returns everything after the first non-empty line', () => {
    const prompt = 'Title line\n\nBody paragraph 1.\n\nBody paragraph 2.'
    expect(extractTaskBody(prompt)).toBe(
      'Body paragraph 1.\n\nBody paragraph 2.'
    )
  })

  it('returns empty when prompt is a single line', () => {
    expect(extractTaskBody('Single line')).toBe('')
  })

  it('handles leading blank lines before the title', () => {
    const prompt = '\n\nTitle\n\nBody'
    expect(extractTaskBody(prompt)).toBe('Body')
  })
})
