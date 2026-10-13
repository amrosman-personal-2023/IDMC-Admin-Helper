import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { render } from '@testing-library/react'
import AdminGuard from '../../admin/components/AdminGuard'
import { AdminAuthProvider } from '../../admin/context/AdminAuthContext'
import { stubFetch, ADMIN_VALID } from './helpers'

beforeEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

function renderGuarded(validateResponse: { ok: boolean; status: number; json: unknown }) {
  stubFetch([validateResponse])
  return render(
    <MemoryRouter initialEntries={['/admin/dashboard']}>
      <AdminAuthProvider>
        <Routes>
          <Route path="/admin/login" element={<p data-testid="login-page">Login</p>} />
          <Route path="/admin/dashboard" element={
            <AdminGuard><p data-testid="protected-content">Dashboard</p></AdminGuard>
          } />
        </Routes>
      </AdminAuthProvider>
    </MemoryRouter>
  )
}

describe('AdminGuard', () => {
  it('renders protected content when authenticated', async () => {
    renderGuarded({ ok: true, status: 200, json: ADMIN_VALID })
    await waitFor(() => expect(screen.getByTestId('protected-content')).toBeInTheDocument())
  })

  it('redirects to /admin/login when unauthenticated', async () => {
    renderGuarded({ ok: false, status: 401, json: {} })
    await waitFor(() => expect(screen.getByTestId('login-page')).toBeInTheDocument())
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })

  it('does not render protected content during redirect', async () => {
    renderGuarded({ ok: false, status: 401, json: {} })
    await waitFor(() => expect(screen.getByTestId('login-page')).toBeInTheDocument())
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument()
  })
})
