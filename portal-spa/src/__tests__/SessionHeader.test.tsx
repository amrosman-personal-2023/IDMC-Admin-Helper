import React from 'react'
import { screen, waitFor, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from '@testing-library/react'
import SessionHeader from '../components/SessionHeader'

beforeEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})
afterEach(() => {
  vi.useRealTimers()
})

function renderHeader(secondsLeft: number, showBanner = false) {
  const onDismiss = vi.fn()
  const onRenewed = vi.fn()
  render(
    <SessionHeader
      secondsLeft={secondsLeft}
      showRenewalBanner={showBanner}
      onDismiss={onDismiss}
      onRenewed={onRenewed}
    />
  )
  return { onDismiss, onRenewed }
}

// ── Countdown display ──────────────────────────────────────────────────────

describe('session countdown', () => {
  it('renders countdown with correct minutes and seconds', () => {
    renderHeader(1800)
    expect(screen.getByTestId('session-countdown')).toHaveTextContent('30:00')
  })

  it('renders 5:00 at 300 seconds', () => {
    renderHeader(300)
    expect(screen.getByTestId('session-countdown')).toHaveTextContent('5:00')
  })

  it('renders 0:00 at 0 seconds', () => {
    renderHeader(0)
    expect(screen.getByTestId('session-countdown')).toHaveTextContent('0:00')
  })
})

// ── Renewal banner ─────────────────────────────────────────────────────────

describe('renewal banner', () => {
  it('does not show banner when showRenewalBanner is false', () => {
    renderHeader(300, false)
    expect(screen.queryByTestId('renewal-banner')).not.toBeInTheDocument()
  })

  it('shows banner when showRenewalBanner is true', () => {
    renderHeader(300, true)
    expect(screen.getByTestId('renewal-banner')).toBeInTheDocument()
  })

  it('calls onDismiss when dismiss button clicked', async () => {
    const { onDismiss } = renderHeader(300, true)
    await userEvent.click(screen.getByRole('button', { name: /dismiss/i }))
    expect(onDismiss).toHaveBeenCalledOnce()
  })

  it('calls onRenewed with new expiry after successful renewal', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: true, status: 200,
      json: () => Promise.resolve({ expires_at: '2026-01-01T14:00:00' }),
    } as Response)

    const { onRenewed } = renderHeader(300, true)
    const user = userEvent.setup()
    await user.type(screen.getByTestId('renewal-totp-input'), '123456')
    await user.click(screen.getByRole('button', { name: /renew/i }))

    await waitFor(() => expect(onRenewed).toHaveBeenCalledWith('2026-01-01T14:00:00'))
  })

  it('shows error message when renewal fails', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValueOnce({
      ok: false, status: 401,
      json: () => Promise.resolve({}),
    } as Response)

    renderHeader(300, true)
    const user = userEvent.setup()
    await user.type(screen.getByTestId('renewal-totp-input'), '000000')
    await user.click(screen.getByRole('button', { name: /renew/i }))

    await waitFor(() => {
      // The error <p> is nested inside the banner which also has a status role.
      // Target it by test id to avoid multi-match.
      const banner = screen.getByTestId('renewal-banner')
      expect(banner.textContent).toMatch(/rejected|failed/i)
    })
  })
})

// ── useSession countdown timing ────────────────────────────────────────────

describe('useSession hook', () => {
  it('starts renewal banner at 5 minutes remaining', async () => {
    vi.useFakeTimers()

    // expires_at = exactly now + 5 min; after one 1-second tick secondsLeft
    // will be ≤ RENEWAL_WARNING_SECONDS (300) which triggers the banner.
    const expiresAt = new Date(Date.now() + 5 * 60 * 1000).toISOString()

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true, status: 200,
      json: () => Promise.resolve({
        valid: true, vendor_id: 1, role: 'vendor_standard', expires_at: expiresAt,
      }),
    } as Response)

    const { useSession } = await import('../hooks/useSession')

    function Probe() {
      const { showRenewalBanner } = useSession()
      return <span data-testid="banner">{showRenewalBanner ? 'yes' : 'no'}</span>
    }

    render(<Probe />)

    // Flush the fetch promise (microtask queue) so useSession sets the timer
    await act(async () => {})

    // Advance the fake clock by one tick so the interval callback fires
    act(() => { vi.advanceTimersByTime(1000) })

    // Synchronous assertion — no waitFor (it uses setTimeout internally)
    expect(screen.getByTestId('banner')).toHaveTextContent('yes')

    vi.useRealTimers()
  })
})
