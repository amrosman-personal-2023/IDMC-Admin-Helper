import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { render } from '@testing-library/react'
import AdminLoginPage from '../../admin/components/AdminLoginPage'
import { AdminAuthProvider } from '../../admin/context/AdminAuthContext'
import { stubFetch, ADMIN_VALID, ADMIN_401 } from './helpers'

beforeEach(() => {
  vi.restoreAllMocks()
  vi.useRealTimers()
})

function renderLogin(initialPath = '/admin/login') {
  return render(
    <MemoryRouter initialEntries={[initialPath]}>
      <AdminAuthProvider>
        <AdminLoginPage />
      </AdminAuthProvider>
    </MemoryRouter>
  )
}

// ── Field rendering ────────────────────────────────────────────────────────

describe('field rendering', () => {
  it('renders username and password fields', () => {
    stubFetch([{ ok: false, status: 401, json: {} }]) // validate → not authenticated
    renderLogin()
    expect(screen.getByTestId('admin-username')).toBeInTheDocument()
    expect(screen.getByTestId('admin-password')).toBeInTheDocument()
  })

  it('does NOT render a TOTP field', () => {
    stubFetch([{ ok: false, status: 401, json: {} }])
    renderLogin()
    expect(screen.queryByTestId('totp-input')).not.toBeInTheDocument()
    expect(screen.queryByText(/authenticator/i)).not.toBeInTheDocument()
  })

  it('has no shared state with vendor login page', () => {
    // Admin login uses AdminAuthContext; vendor uses no context.
    // Verify the form has aria-label "Admin login form", not "Login form".
    stubFetch([{ ok: false, status: 401, json: {} }])
    renderLogin()
    expect(screen.getByRole('form', { name: /admin login form/i })).toBeInTheDocument()
    expect(screen.queryByRole('form', { name: /^login form$/i })).not.toBeInTheDocument()
  })
})

// ── Login flow ─────────────────────────────────────────────────────────────

describe('login flow', () => {
  it('shows generic error on failed login — no detail', async () => {
    stubFetch([
      { ok: false, status: 401, json: {} }, // validate
      { ok: false, status: 401, json: { detail: 'authentication failed' } }, // login
    ])
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByTestId('admin-username'), 'admin')
    await user.type(screen.getByTestId('admin-password'), 'wrong')
    await user.click(screen.getByTestId('admin-login-btn'))
    await waitFor(() => {
      const err = screen.getByTestId('admin-login-error')
      expect(err).toHaveTextContent('Login failed')
      expect(err.textContent).not.toMatch(/authentication failed/i)
      expect(err.textContent).not.toMatch(/detail/i)
    })
  })

  it('shows lockout warning after multiple failures', async () => {
    const fail = { ok: false, status: 401, json: {} }
    // validate + 5 login failures
    stubFetch([fail, fail, fail, fail, fail, fail])
    const user = userEvent.setup()
    renderLogin()
    for (let i = 0; i < 5; i++) {
      await user.clear(screen.getByTestId('admin-password'))
      await user.type(screen.getByTestId('admin-password'), 'wrong')
      await user.click(screen.getByTestId('admin-login-btn'))
      await waitFor(() => screen.getByTestId('admin-login-error'))
    }
    expect(screen.getByTestId('lockout-warning')).toBeInTheDocument()
  })

  it('redirects to /admin/dashboard on success', async () => {
    stubFetch([
      { ok: false, status: 401, json: {} },
      { ok: true,  status: 200, json: { logged_in: true, expires_at: '2026-01-01T20:00:00' } },
      { ok: true,  status: 200, json: ADMIN_VALID },
    ])
    const user = userEvent.setup()
    // Provide the dashboard route so navigate('/admin/dashboard') can resolve
    render(
      <MemoryRouter initialEntries={['/admin/login']}>
        <AdminAuthProvider>
          <Routes>
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route path="/admin/dashboard" element={<p data-testid="dashboard">Dashboard</p>} />
          </Routes>
        </AdminAuthProvider>
      </MemoryRouter>
    )
    await user.type(screen.getByTestId('admin-username'), 'sysadmin')
    await user.type(screen.getByTestId('admin-password'), 'correct!')
    await user.click(screen.getByTestId('admin-login-btn'))
    await waitFor(() => expect(screen.getByTestId('dashboard')).toBeInTheDocument())
    expect(screen.queryByTestId('admin-login-btn')).not.toBeInTheDocument()
  })

  it('nothing stored in localStorage or sessionStorage after login', async () => {
    stubFetch([
      { ok: false, status: 401, json: {} },
      { ok: true, status: 200, json: { logged_in: true, expires_at: '2026-01-01T20:00:00' } },
      { ok: true, status: 200, json: ADMIN_VALID },
    ])
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/login']}>
        <AdminAuthProvider>
          <Routes>
            <Route path="/admin/login" element={<AdminLoginPage />} />
            <Route path="/admin/dashboard" element={<p data-testid="dashboard">Dashboard</p>} />
          </Routes>
        </AdminAuthProvider>
      </MemoryRouter>
    )
    await user.type(screen.getByTestId('admin-username'), 'a')
    await user.type(screen.getByTestId('admin-password'), 'b')
    await user.click(screen.getByTestId('admin-login-btn'))
    await waitFor(() => expect(screen.getByTestId('dashboard')).toBeInTheDocument())
    expect(localStorage.length).toBe(0)
    expect(sessionStorage.length).toBe(0)
  })
})

// ── Vendor cookie rejected ─────────────────────────────────────────────────

describe('access control', () => {
  it('shows access denied when server returns 403', async () => {
    stubFetch([
      { ok: false, status: 401, json: {} }, // validate
      { ok: false, status: 403, json: {} }, // login attempt → 403
    ])
    const user = userEvent.setup()
    renderLogin()
    await user.type(screen.getByTestId('admin-username'), 'vendor')
    await user.type(screen.getByTestId('admin-password'), 'vendorpass')
    await user.click(screen.getByTestId('admin-login-btn'))
    await waitFor(() => expect(screen.getByTestId('admin-login-error')).toBeInTheDocument())
  })
})
