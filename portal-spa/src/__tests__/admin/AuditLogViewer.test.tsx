import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { render } from '@testing-library/react'
import AuditLogViewer from '../../admin/components/AuditLogViewer'
import { stubFetch } from './helpers'

beforeEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

const AUDIT_ROWS = [
  { id: 1, event_type: 'vendor_login_success', subject_id: 1, subject_type: 'vendor',
    vendor_id: 1, timestamp: '2026-01-01T12:00:00', source_ip: '1.2.3.4', action_detail: {} },
  { id: 2, event_type: 'file_upload', subject_id: 1, subject_type: 'vendor',
    vendor_id: 1, timestamp: '2026-01-01T12:01:00', source_ip: '1.2.3.4', action_detail: {} },
]
const VENDORS = [{ id: 1, username: 'acme', role: 'vendor_standard', created_at: '2026-01-01', active: true, device_count: 1 }]

function renderAudit(initialSearch = '') {
  stubFetch([
    { ok: true, status: 200, json: VENDORS },
    { ok: true, status: 200, json: { page: 1, page_size: 50, results: AUDIT_ROWS } },
  ])
  return render(
    <MemoryRouter initialEntries={[`/admin/audit${initialSearch}`]}>
      <Routes>
        <Route path="/admin/audit" element={<AuditLogViewer />} />
      </Routes>
    </MemoryRouter>
  )
}

// ── Audit table ────────────────────────────────────────────────────────────

describe('audit table', () => {
  it('renders audit rows', async () => {
    renderAudit()
    await waitFor(() => expect(screen.getByTestId('audit-row-1')).toBeInTheDocument())
    expect(screen.getByTestId('audit-row-2')).toBeInTheDocument()
  })
})

// ── Filters update URL ─────────────────────────────────────────────────────

describe('filters update URL query params', () => {
  it('vendor filter updates URL and triggers new API call', async () => {
    const fetchSpy = stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: { page: 1, page_size: 50, results: AUDIT_ROWS } },
      { ok: true, status: 200, json: { page: 1, page_size: 50, results: [] } }, // after filter
    ])
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/audit']}>
        <Routes><Route path="/admin/audit" element={<AuditLogViewer />} /></Routes>
      </MemoryRouter>
    )
    await waitFor(() => screen.getByTestId('filter-vendor'))
    await user.selectOptions(screen.getByTestId('filter-vendor'), '1')
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(3))
    // Third call URL must contain vendor_id=1
    const lastUrl = (fetchSpy.mock.calls[2][0] as string)
    expect(lastUrl).toContain('vendor_id=1')
  })

  it('event_type filter updates URL and API call', async () => {
    const fetchSpy = stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: { page: 1, page_size: 50, results: AUDIT_ROWS } },
      { ok: true, status: 200, json: { page: 1, page_size: 50, results: [] } },
    ])
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/audit']}>
        <Routes><Route path="/admin/audit" element={<AuditLogViewer />} /></Routes>
      </MemoryRouter>
    )
    await waitFor(() => screen.getByTestId('filter-event-type'))
    await user.selectOptions(screen.getByTestId('filter-event-type'), 'login')
    await waitFor(() => expect(fetchSpy).toHaveBeenCalledTimes(3))
    expect(fetchSpy.mock.calls[2][0] as string).toContain('event_type=login')
  })

  it('date_from filter updates API call', async () => {
    const fetchSpy = stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: { page: 1, page_size: 50, results: AUDIT_ROWS } },
      { ok: true, status: 200, json: { page: 1, page_size: 50, results: [] } },
    ])
    const user = userEvent.setup()
    render(
      <MemoryRouter initialEntries={['/admin/audit']}>
        <Routes><Route path="/admin/audit" element={<AuditLogViewer />} /></Routes>
      </MemoryRouter>
    )
    await waitFor(() => screen.getByTestId('filter-date-from'))
    await user.type(screen.getByTestId('filter-date-from'), '2026-01-01')
    await waitFor(() => expect(fetchSpy.mock.calls.length).toBeGreaterThan(2))
    const lastUrl = fetchSpy.mock.calls[fetchSpy.mock.calls.length - 1][0] as string
    expect(lastUrl).toContain('date_from=2026-01-01')
  })
})

// ── CSV export ─────────────────────────────────────────────────────────────

describe('CSV export', () => {
  it('export button triggers file download', async () => {
    stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: { page: 1, page_size: 50, results: AUDIT_ROWS } },
      { ok: true, status: 200, text: 'id,event_type\n1,login\n' }, // CSV response
    ])

    // jsdom does not implement URL.createObjectURL — assign stubs directly
    const clickSpy = vi.fn()
    ;(globalThis as any).URL.createObjectURL = vi.fn().mockReturnValue('blob:test')
    ;(globalThis as any).URL.revokeObjectURL = vi.fn()
    const origCreate = document.createElement.bind(document)
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) => {
      if (tag === 'a') {
        const a = origCreate('a') as HTMLAnchorElement
        a.click = clickSpy
        return a
      }
      return origCreate(tag)
    })

    const user = userEvent.setup()
    renderAudit()
    await waitFor(() => screen.getByTestId('export-csv-btn'))
    await user.click(screen.getByTestId('export-csv-btn'))

    await waitFor(() => expect(clickSpy).toHaveBeenCalled())
    expect((globalThis as any).URL.createObjectURL).toHaveBeenCalled()
  })
})
