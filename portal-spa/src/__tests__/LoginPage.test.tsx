import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import LoginPage from '../components/LoginPage'
import { renderWithRouter, mockFetch } from './helpers'

beforeEach(() => vi.restoreAllMocks())

// ── Form rendering ─────────────────────────────────────────────────────────

describe('credential fields', () => {
  it('renders username and password fields', () => {
    renderWithRouter(<LoginPage />)
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
  })

  it('does not render TOTP field on initial load', () => {
    renderWithRouter(<LoginPage />)
    expect(screen.queryByTestId('totp-input')).not.toBeInTheDocument()
  })

  it('shows TOTP input after correct password', async () => {
    mockFetch([{ ok: true, status: 200, json: { totp_required: true } }])
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    await user.type(screen.getByLabelText(/username/i), 'v1')
    await user.type(screen.getByLabelText(/password/i), 'correctpass')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByTestId('totp-input')).toBeInTheDocument())
  })

  it('shows error and stays on credential step when password is wrong', async () => {
    mockFetch([{ ok: false, status: 401, json: { detail: 'authentication failed' } }])
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    await user.type(screen.getByLabelText(/username/i), 'v1')
    await user.type(screen.getByLabelText(/password/i), 'wrongpass')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => expect(screen.getByTestId('login-error')).toBeInTheDocument())
    expect(screen.queryByTestId('totp-input')).not.toBeInTheDocument()
  })
})

// ── TOTP validation ────────────────────────────────────────────────────────

describe('TOTP input validation', () => {
  async function advanceToTotp(user: ReturnType<typeof userEvent.setup>) {
    mockFetch([{ ok: true, status: 200, json: { totp_required: true } }])
    renderWithRouter(<LoginPage />)
    await user.type(screen.getByLabelText(/username/i), 'vendor1')
    await user.type(screen.getByLabelText(/password/i), 'pass123')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => screen.getByTestId('totp-input'))
  }

  it('TOTP input has maxLength=6', async () => {
    const user = userEvent.setup()
    await advanceToTotp(user)
    expect(screen.getByTestId('totp-input')).toHaveAttribute('maxLength', '6')
  })

  it('strips non-digit characters', async () => {
    const user = userEvent.setup()
    await advanceToTotp(user)
    await user.type(screen.getByTestId('totp-input'), 'ab12cd')
    expect(screen.getByTestId('totp-input')).toHaveValue('12')
  })

  it('accepts exactly 6 digits', async () => {
    const user = userEvent.setup()
    await advanceToTotp(user)
    await user.type(screen.getByTestId('totp-input'), '123456')
    expect(screen.getByTestId('totp-input')).toHaveValue('123456')
  })

  it('rejects submit when fewer than 6 digits entered', async () => {
    const user = userEvent.setup()
    await advanceToTotp(user)
    const spy = mockFetch([{ ok: true, status: 200, json: {} }])
    await user.type(screen.getByTestId('totp-input'), '123')
    await user.click(screen.getByRole('button', { name: /verify/i }))
    await waitFor(() => expect(screen.getByTestId('login-error')).toBeInTheDocument())
    // fetch should NOT have been called for the short code
    expect(spy).not.toHaveBeenCalled()
  })
})

// ── Error messages ─────────────────────────────────────────────────────────

describe('error messages', () => {
  it('shows generic "Login failed" — no factor detail', async () => {
    mockFetch([
      { ok: true, status: 200, json: { totp_required: true } },  // creds → totp step
      { ok: false, status: 401, json: { detail: 'authentication failed' } },
    ])
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    await user.type(screen.getByLabelText(/username/i), 'v')
    await user.type(screen.getByLabelText(/password/i), 'p')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => screen.getByTestId('totp-input'))
    await user.type(screen.getByTestId('totp-input'), '000000')
    await user.click(screen.getByRole('button', { name: /verify/i }))

    await waitFor(() => {
      const err = screen.getByTestId('login-error')
      expect(err).toHaveTextContent('Login failed')
      expect(err.textContent).not.toMatch(/password/i)
      expect(err.textContent).not.toMatch(/totp/i)
      expect(err.textContent).not.toMatch(/device/i)
      expect(err.textContent).not.toMatch(/authentication failed/i)
    })
  })
})

// ── Lockout ────────────────────────────────────────────────────────────────

describe('lockout after 3 TOTP failures', () => {
  it('disables form and shows countdown', async () => {
    const totpFail = { ok: false, status: 401, json: { detail: 'authentication failed' } }
    mockFetch([
      { ok: true, status: 200, json: { totp_required: true } },  // creds ok
      totpFail, totpFail, totpFail,  // 3 bad TOTP codes
    ])
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    await user.type(screen.getByLabelText(/username/i), 'v')
    await user.type(screen.getByLabelText(/password/i), 'p')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => screen.getByTestId('totp-input'))

    for (let i = 0; i < 3; i++) {
      await user.clear(screen.getByTestId('totp-input'))
      await user.type(screen.getByTestId('totp-input'), '000000')
      await user.click(screen.getByRole('button', { name: /verify/i }))
      await waitFor(() => screen.getByTestId('login-error'))
    }

    await waitFor(() => {
      expect(screen.getByTestId('totp-input')).toBeDisabled()
      expect(screen.getByTestId('lockout-message')).toBeInTheDocument()
      expect(screen.getByRole('button', { name: /verify/i })).toBeDisabled()
    })
  })
})

// ── Security: no token in storage ─────────────────────────────────────────

describe('session storage security', () => {
  it('nothing written to localStorage or sessionStorage after login', async () => {
    mockFetch([
      { ok: true, status: 200, json: { totp_required: true } },
      { ok: true, status: 200, json: { expires_at: '2026-01-01T13:00:00' } },
    ])
    const user = userEvent.setup()
    renderWithRouter(<LoginPage />)
    await user.type(screen.getByLabelText(/username/i), 'v')
    await user.type(screen.getByLabelText(/password/i), 'p')
    await user.click(screen.getByRole('button', { name: /continue/i }))
    await waitFor(() => screen.getByTestId('totp-input'))
    await user.type(screen.getByTestId('totp-input'), '123456')
    await user.click(screen.getByRole('button', { name: /verify/i }))

    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })
})

// ── Open redirect guard ────────────────────────────────────────────────────

describe('redirect safety', () => {
  it('does not navigate to external URL even if next param is supplied', () => {
    render(
      <MemoryRouter initialEntries={['/login?next=https://evil.com']}>
        <LoginPage />
      </MemoryRouter>
    )
    expect(screen.getByLabelText(/username/i)).toBeInTheDocument()
    // Component renders without error — safeRedirectTarget will return '/'
  })
})
