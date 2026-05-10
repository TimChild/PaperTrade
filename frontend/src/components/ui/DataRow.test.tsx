import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import {
  DataTable,
  DataTableHead,
  DataTableBody,
  DataHeaderCell,
  DataRow,
  DataCell,
} from './DataRow'

describe('DataRow primitives', () => {
  it('renders a data table with rows', () => {
    render(
      <DataTable testId="holdings-table">
        <DataTableHead>
          <DataHeaderCell>Symbol</DataHeaderCell>
          <DataHeaderCell align="right">Shares</DataHeaderCell>
        </DataTableHead>
        <DataTableBody>
          <DataRow testId="row-AAPL">
            <DataCell emphasis="primary">AAPL</DataCell>
            <DataCell align="right" numeric tone="muted" testId="aapl-shares">
              100
            </DataCell>
          </DataRow>
        </DataTableBody>
      </DataTable>
    )

    expect(screen.getByTestId('holdings-table')).toBeInTheDocument()
    expect(screen.getByTestId('row-AAPL')).toBeInTheDocument()
    expect(screen.getByText('AAPL')).toBeInTheDocument()
  })

  it('numeric cells use tabular mono', () => {
    render(
      <DataTable>
        <DataTableBody>
          <DataRow>
            <DataCell numeric testId="num">
              $1,000.00
            </DataCell>
          </DataRow>
        </DataTableBody>
      </DataTable>
    )
    const cell = screen.getByTestId('num')
    expect(cell).toHaveClass('font-tabular')
  })

  it('applies gain tone class', () => {
    render(
      <DataTable>
        <DataTableBody>
          <DataRow>
            <DataCell tone="gain" numeric testId="gain-cell">
              +$1,000
            </DataCell>
          </DataRow>
        </DataTableBody>
      </DataTable>
    )
    expect(screen.getByTestId('gain-cell')).toHaveClass('text-gain')
  })

  it('applies loss tone class', () => {
    render(
      <DataTable>
        <DataTableBody>
          <DataRow>
            <DataCell tone="loss" numeric testId="loss-cell">
              -$200
            </DataCell>
          </DataRow>
        </DataTableBody>
      </DataTable>
    )
    expect(screen.getByTestId('loss-cell')).toHaveClass('text-loss')
  })

  it('renders header cells with the eyebrow font class', () => {
    render(
      <DataTable>
        <DataTableHead>
          <DataHeaderCell>Symbol</DataHeaderCell>
        </DataTableHead>
      </DataTable>
    )
    const header = screen.getByText('Symbol')
    expect(header).toHaveClass('font-eyebrow')
  })

  it('hides cells on mobile when hideOnMobile is true', () => {
    render(
      <DataTable>
        <DataTableBody>
          <DataRow>
            <DataCell hideOnMobile testId="hidden-cell">
              hidden
            </DataCell>
          </DataRow>
        </DataTableBody>
      </DataTable>
    )
    expect(screen.getByTestId('hidden-cell').className).toContain('hidden')
    expect(screen.getByTestId('hidden-cell').className).toContain(
      'sm:table-cell'
    )
  })

  it('interactive rows include hover styling', () => {
    render(
      <DataTable>
        <DataTableBody>
          <DataRow interactive testId="interactive-row">
            <DataCell>x</DataCell>
          </DataRow>
        </DataTableBody>
      </DataTable>
    )
    expect(screen.getByTestId('interactive-row').className).toContain(
      'hover:bg-canvas-raised'
    )
  })
})
