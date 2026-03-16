import { afterEach, describe, expect, it, vi } from 'vitest'
import { resolveApiBaseUrl } from '../client'

describe('resolveApiBaseUrl', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('uses localhost backend by default in development', () => {
    expect(resolveApiBaseUrl({ mode: 'development' })).toBe('http://localhost:8000/api/v1')
  })

  it('uses same-origin api path by default in production', () => {
    expect(resolveApiBaseUrl({ mode: 'production' })).toBe('/api/v1')
  })

  it('falls back to same-origin api when production config points at api subdomain', () => {
    const warnSpy = vi.spyOn(console, 'warn').mockImplementation(() => {})

    expect(
      resolveApiBaseUrl({
        mode: 'production',
        configuredBaseUrl: 'https://api.zebutrader.com/api/v1',
        windowOrigin: 'https://zebutrader.com',
      })
    ).toBe('/api/v1')

    expect(warnSpy).toHaveBeenCalledOnce()
  })

  it('preserves explicit production config for other deployments', () => {
    expect(
      resolveApiBaseUrl({
        mode: 'production',
        configuredBaseUrl: 'https://api.example.com/api/v1',
        windowOrigin: 'https://app.example.com',
      })
    ).toBe('https://api.example.com/api/v1')
  })
})
