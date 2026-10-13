import React, { ReactElement } from 'react'
import { render, RenderOptions } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { AdminAuthProvider } from '../../admin/context/AdminAuthContext'

/** Wrap admin components with the router and auth context they need. */
export function renderAdmin(
  ui: ReactElement,
  { initialPath = '/admin/dashboard', ...options }: RenderOptions & { initialPath?: string } = {}
) {
  function Wrapper({ children }: { children: React.ReactNode }) {
    return (
      <MemoryRouter initialEntries={[initialPath]}>
        <AdminAuthProvider>{children}</AdminAuthProvider>
      </MemoryRouter>
    )
  }
  return render(ui, { wrapper: Wrapper, ...options })
}

/** Stub fetch with a sequence of responses. */
export function stubFetch(responses: Array<{ ok: boolean; status: number; json?: unknown; text?: string }>) {
  let i = 0
  return vi.spyOn(globalThis, 'fetch').mockImplementation(() => {
    const r = responses[Math.min(i++, responses.length - 1)]
    return Promise.resolve({
      ok: r.ok,
      status: r.status,
      blob: () => Promise.resolve(new Blob([r.text ?? ''], { type: 'text/csv' })),
      json: () => Promise.resolve(r.json ?? {}),
      text: () => Promise.resolve(r.text ?? ''),
    } as Response)
  })
}

export const ADMIN_VALID = { valid: true, admin_id: 1, role: 'admin', expires_at: '2026-01-01T20:00:00' }
export const ADMIN_401 = { ok: false, status: 401, json: {} }
export const ADMIN_403 = { ok: false, status: 403, json: {} }
