/**
 * Tests for useDebounce hook
 */
import { describe, it, expect } from 'vitest'
import { renderHook, waitFor } from '@testing-library/react'
import { useDebounce } from '../useDebounce'

describe('useDebounce', () => {
  it('should return initial value immediately', () => {
    const { result } = renderHook(() => useDebounce('initial', 500))
    expect(result.current).toBe('initial')
  })

  it('should debounce value changes', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: { value: 'initial', delay: 100 },
      }
    )

    expect(result.current).toBe('initial')

    // Update the value
    rerender({ value: 'updated', delay: 100 })

    // Value should not change immediately
    expect(result.current).toBe('initial')

    // Wait for debounce delay
    await waitFor(
      () => {
        expect(result.current).toBe('updated')
      },
      { timeout: 500 }
    )
  })

  it('should reset timer on rapid value changes', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: { value: 'initial', delay: 100 },
      }
    )

    // Rapidly change values with small delays between
    rerender({ value: 'change1', delay: 100 })
    await new Promise((resolve) => setTimeout(resolve, 50))

    rerender({ value: 'change2', delay: 100 })
    await new Promise((resolve) => setTimeout(resolve, 50))

    rerender({ value: 'change3', delay: 100 })

    // Should still be initial because we haven't waited full delay
    expect(result.current).toBe('initial')

    // Now wait the full delay after the last change
    await waitFor(
      () => {
        expect(result.current).toBe('change3')
      },
      { timeout: 500 }
    )
  })

  it('should work with different value types', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: { value: 123, delay: 100 },
      }
    )

    expect(result.current).toBe(123)

    rerender({ value: 456, delay: 100 })

    await waitFor(
      () => {
        expect(result.current).toBe(456)
      },
      { timeout: 500 }
    )
  })

  it('should handle object values', async () => {
    const obj1 = { id: 1, name: 'test' }
    const obj2 = { id: 2, name: 'updated' }

    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: { value: obj1, delay: 100 },
      }
    )

    expect(result.current).toBe(obj1)

    rerender({ value: obj2, delay: 100 })

    await waitFor(
      () => {
        expect(result.current).toBe(obj2)
      },
      { timeout: 500 }
    )
  })

  it('should handle empty string', async () => {
    const { result, rerender } = renderHook(
      ({ value, delay }) => useDebounce(value, delay),
      {
        initialProps: { value: '', delay: 100 },
      }
    )

    expect(result.current).toBe('')

    rerender({ value: 'not empty', delay: 100 })

    await waitFor(
      () => {
        expect(result.current).toBe('not empty')
      },
      { timeout: 500 }
    )
  })
})
