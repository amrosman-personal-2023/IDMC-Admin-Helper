import React from 'react'
import { screen, waitFor, act, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import SessionOverview from '../../admin/components/SessionOverview'
import { stubFetch } from './helpers'

beforeEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })
afterEach(() => { vi.useRealTimers() })

const SESSIONS = [
  { id: 10, subject_id: 1, subject_type: 'vendor', role: 'vendor_standard',
    created_at: '2026-01-01T12:00:00', last_active_at: '2026-01-01T12:05:00',
    expires_at: '2026-01-01T12:30:00', source_ip: '1.2.3.4' },
  { id: 11, subject_id: 1, subject_type: 'admin', role: 'admin',
    created_at: '2026-01-01T11:00:00', last_active_at: '2026-01-01T12:00:00',
    expires_at: '2026-01-01T19:00:00', source_ip: '10.0.0.1' },
]

function renderSessions() {
  return render(<MemoryRouter><SessionOverview /></MemoryRouter>)
}

// ── Rendering ──────────────────────────────────────────────────────────────

describe('session table', () => {
  it('renders session rows', async () => {
    stubFetch([{ ok: true, status: 200, json: SESSIONS }])
    renderSessions()
    await waitFor(() => expect(screen.getByTestId('session-row-10')).toBeInTheDocument())
    expect(screen.getByTestId('session-row-11')).toBeInTheDocument()
  })
})

// ── Auto-refresh ───────────────────────────────────────────────────────────

describe('auto-refresh every 15 seconds', () => {
  it('re-fetches sessions after 15 s', () => {
    vi.useFakeTimers()
    const fetchSpy = stubFetch([
      { ok: true, status: 200, json: SESSIONS },
      { ok: true, status: 200, json: SESSIONS },
    ])
    render(<MemoryRouter><SessionOverview /></MemoryRouter>)

    act(() => { vi.advanceTimersByTime(15_000) })

    // initial load + one refresh
    expect(fetchSpy).toHaveBeenCalledTimes(2)
    vi.useRealTimers()
  })
})

// ── Force expire ───────────────────────────────────────────────────────────

describe('force expire session', () => {
  it('shows confirmation dialog before expiring', async () => {
    stubFetch([{ ok: true, status: 200, json: SESSIONS }])
    renderSessions()
    await waitFor(() => screen.getByTestId('expire-btn-10'))
    await userEvent.click(screen.getByTestId('expire-btn-10'))
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
  })

  it('removes session from table after confirmed expiry', async () => {
    stubFetch([
      { ok: true, status: 200, json: SESSIONS },
      { ok: true, status: 200, json: { expired: true } },
    ])
    const user = userEvent.setup()
    renderSessions()
    await waitFor(() => screen.getByTestId('expire-btn-10'))
    await user.click(screen.getByTestId('expire-btn-10'))
    await user.click(screen.getByTestId('confirm-ok'))
    await waitFor(() =>
      expect(screen.queryByTestId('session-row-10')).not.toBeInTheDocument()
    )
    // Other session still present
    expect(screen.getByTestId('session-row-11')).toBeInTheDocument()
  })

  it('does not expire if user cancels', async () => {
    const fetchSpy = stubFetch([{ ok: true, status: 200, json: SESSIONS }])
    const user = userEvent.setup()
    renderSessions()
    await waitFor(() => screen.getByTestId('expire-btn-10'))
    await user.click(screen.getByTestId('expire-btn-10'))
    await user.click(screen.getByTestId('confirm-cancel'))
    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument()
    expect(fetchSpy).toHaveBeenCalledTimes(1) // only initial load
    expect(screen.getByTestId('session-row-10')).toBeInTheDocument()
  })
})
