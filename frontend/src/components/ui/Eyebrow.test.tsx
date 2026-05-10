import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Eyebrow } from './Eyebrow'

describe('Eyebrow', () => {
  it('renders children', () => {
    render(<Eyebrow>Updated</Eyebrow>)
    expect(screen.getByText('Updated')).toBeInTheDocument()
  })

  it('uses the eyebrow font class (small caps + tracking)', () => {
    render(<Eyebrow>Hello</Eyebrow>)
    const el = screen.getByText('Hello')
    expect(el).toHaveClass('font-eyebrow')
  })

  it('renders accent tone when requested', () => {
    render(<Eyebrow tone="accent">Live</Eyebrow>)
    const el = screen.getByText('Live')
    expect(el).toHaveClass('text-amber')
  })
})
