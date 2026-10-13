import React from 'react'
import { screen, waitFor, act, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import ScriptOperationsView from '../components/ScriptOperationsView'
import { OperationDef } from '../api/backend'

// Guarantee real timers are restored before every test, even if a previous
// test timed out before its own cleanup ran.
beforeEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})
afterEach(() => {
  vi.useRealTimers()
})

const OPS: OperationDef[] = [
  { name: 'daily_load', description: 'Run the daily data load script' },
  { name: 'param_reload', description: 'Reload parameter files' },
]

// ── Rendering ──────────────────────────────────────────────────────────────

describe('rendering', () => {
  it('renders each operation as a named button', () => {
    render(<ScriptOperationsView operations={OPS} />)
    expect(screen.getByTestId('run-btn-daily_load')).toBeInTheDocument()
    expect(screen.getByTestId('run-btn-param_reload')).toBeInTheDocument()
  })

  it('shows empty state when no operations', () => {
    render(<ScriptOperationsView operations={[]} />)
    expect(screen.getByText(/no operations/i)).toBeInTheDocument()
  })

  it('role-based: only shows operations passed in props', () => {
    render(<ScriptOperationsView operations={[OPS[0]]} />)
    expect(screen.getByTestId('run-btn-daily_load')).toBeInTheDocument()
    expect(screen.queryByTestId('run-btn-param_reload')).not.toBeInTheDocument()
  })
})

// ── Button disabled during in-flight operation ─────────────────────────────

describe('button disabled while running', () => {
  it('disables run button while operation is in flight', async () => {
    let resolveRun!: (v: unknown) => void
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(
      () => new Promise((res) => { resolveRun = res })
    )

    const user = userEvent.setup()
    render(<ScriptOperationsView operations={[OPS[0]]} />)
    await user.click(screen.getByTestId('run-btn-daily_load'))

    expect(screen.getByTestId('run-btn-daily_load')).toBeDisabled()

    resolveRun({
      ok: true, status: 200,
      json: () => Promise.resolve({
        operation: 'daily_load', exit_code: 0, output: 'done', duration_ms: 100,
      }),
    })
    await waitFor(() => expect(screen.getByTestId('run-btn-daily_load')).not.toBeDisabled())
  })

  it('shows elapsed time counter while running', () => {
    vi.useFakeTimers()

    let resolveRun!: (v: unknown) => void
    vi.spyOn(globalThis, 'fetch').mockImplementationOnce(
      () => new Promise((res) => { resolveRun = res })
    )

    render(<ScriptOperationsView operations={[OPS[0]]} />)

    // fireEvent is fully synchronous — safe to use with fake timers
    act(() => { fireEvent.click(screen.getByTestId('run-btn-daily_load')) })

    // Advance clock 2 seconds so the interval callback fires twice
    act(() => { vi.advanceTimersByTime(2000) })

    expect(screen.getByTestId('elapsed-daily_load')).toHaveTextContent('2s')

    // Resolve the pending fetch and restore timers
    resolveRun({
      ok: true, status: 200,
      json: () => Promise.resolve({ operation: 'daily_load', exit_code: 0, output: '', duration_ms: 2000 }),
    })
    vi.useRealTimers()
  })
})

// ── Completion ─────────────────────────────────────────────────────────────

describe('completion display', () => {
  it('shows exit code, duration, and truncated output', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true, status: 200,
      json: () => Promise.resolve({
        operation: 'daily_load',
        exit_code: 0,
        output: 'A'.repeat(3000),
        duration_ms: 450,
      }),
    } as Response)

    const user = userEvent.setup()
    render(<ScriptOperationsView operations={[OPS[0]]} />)
    await user.click(screen.getByTestId('run-btn-daily_load'))

    await waitFor(() => expect(screen.getByTestId('result-daily_load')).toBeInTheDocument())
    expect(screen.getByTestId('result-daily_load')).toHaveTextContent('Exit code: 0')
    expect(screen.getByTestId('result-daily_load')).toHaveTextContent('450ms')
    const out = screen.getByTestId('output-daily_load').textContent ?? ''
    expect(out.length).toBeLessThanOrEqual(2000)
  })

  it('shows timeout message when operation times out', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false, status: 504,
      json: () => Promise.resolve({ detail: 'operation timed out' }),
    } as Response)

    const user = userEvent.setup()
    render(<ScriptOperationsView operations={[OPS[0]]} />)
    await user.click(screen.getByTestId('run-btn-daily_load'))

    await waitFor(() =>
      expect(screen.getByTestId('timeout-daily_load')).toHaveTextContent(/timed out/i)
    )
  })

  it('shows user-friendly error on failure', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false, status: 500,
      json: () => Promise.resolve({ detail: 'internal error' }),
    } as Response)

    const user = userEvent.setup()
    render(<ScriptOperationsView operations={[OPS[0]]} />)
    await user.click(screen.getByTestId('run-btn-daily_load'))

    await waitFor(() => expect(screen.getByTestId('error-daily_load')).toBeInTheDocument())
    expect(screen.getByTestId('error-daily_load').textContent).not.toContain('internal error')
    expect(screen.getByTestId('error-daily_load').textContent).not.toContain('Traceback')
  })
})

// ── Role-based rendering ───────────────────────────────────────────────────

describe('role-based rendering', () => {
  it('vendor_standard does not see premium-only operations', () => {
    render(<ScriptOperationsView operations={[OPS[0]]} />)
    expect(screen.getByTestId('run-btn-daily_load')).toBeInTheDocument()
    expect(screen.queryByTestId('run-btn-param_reload')).not.toBeInTheDocument()
  })
})
