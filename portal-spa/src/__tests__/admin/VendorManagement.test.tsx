import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import VendorManagement from '../../admin/components/VendorManagement'
import { stubFetch } from './helpers'

beforeEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

const VENDORS = [
  { id: 1, username: 'acme', role: 'vendor_standard', created_at: '2026-01-01', active: true, device_count: 2 },
  { id: 2, username: 'globex', role: 'vendor_premium', created_at: '2026-01-02', active: false, device_count: 1 },
]

function renderPage(extraResponses: Array<{ ok: boolean; status: number; json: unknown }> = []) {
  stubFetch([
    { ok: true, status: 200, json: VENDORS }, // initial listVendors
    ...extraResponses,
  ])
  return render(
    <MemoryRouter><VendorManagement /></MemoryRouter>
  )
}

// ── Vendor table ───────────────────────────────────────────────────────────

describe('vendor table', () => {
  it('renders vendor rows', async () => {
    renderPage()
    await waitFor(() => expect(screen.getByTestId('vendor-row-1')).toBeInTheDocument())
    expect(screen.getByTestId('vendor-row-2')).toBeInTheDocument()
  })

  it('shows active status per vendor', async () => {
    renderPage()
    await waitFor(() => screen.getByTestId('vendor-active-1'))
    expect(screen.getByTestId('vendor-active-1')).toHaveTextContent('Active')
    expect(screen.getByTestId('vendor-active-2')).toHaveTextContent('Inactive')
  })

  it('does not show deactivate button for already-inactive vendor', async () => {
    renderPage()
    await waitFor(() => screen.getByTestId('vendor-row-2'))
    expect(screen.queryByTestId('deactivate-btn-2')).not.toBeInTheDocument()
  })
})

// ── Create vendor ──────────────────────────────────────────────────────────

describe('create vendor', () => {
  it('shows create form on button click', async () => {
    renderPage()
    await waitFor(() => screen.getByTestId('show-create-btn'))
    await userEvent.click(screen.getByTestId('show-create-btn'))
    expect(screen.getByTestId('create-vendor-form')).toBeInTheDocument()
  })

  it('submits form and shows enrollment link dialog', async () => {
    stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: {
        vendor_id: 3, username: 'newco', role: 'vendor_standard',
        otpauth_uri: 'otpauth://totp/IDMC%20Portal:newco?secret=JBSWY3DPEHPK3PXP&issuer=IDMC+Portal',
        qr_data_uri: 'data:image/png;base64,ABC123',
      }},
      { ok: true, status: 200, json: VENDORS }, // reload after create
    ])
    const user = userEvent.setup()
    render(<MemoryRouter><VendorManagement /></MemoryRouter>)
    await waitFor(() => screen.getByTestId('show-create-btn'))
    await user.click(screen.getByTestId('show-create-btn'))
    await user.type(screen.getByTestId('create-username'), 'newco')
    await user.type(screen.getByTestId('create-password'), 'pw123!')
    await user.click(screen.getByTestId('create-submit'))

    await waitFor(() => expect(screen.getByTestId('qr-dialog')).toBeInTheDocument())
    expect(screen.getByTestId('qr-image')).toBeInTheDocument()
    expect(screen.getByTestId('copy-btn')).toBeInTheDocument()
  })
})

// ── Deactivate vendor ──────────────────────────────────────────────────────

describe('deactivate vendor', () => {
  it('shows confirmation dialog before deactivating', async () => {
    renderPage()
    await waitFor(() => screen.getByTestId('deactivate-btn-1'))
    await userEvent.click(screen.getByTestId('deactivate-btn-1'))
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
  })

  it('does not call API if user cancels', async () => {
    const fetchSpy = stubFetch([{ ok: true, status: 200, json: VENDORS }])
    const user = userEvent.setup()
    render(<MemoryRouter><VendorManagement /></MemoryRouter>)
    await waitFor(() => screen.getByTestId('deactivate-btn-1'))
    await user.click(screen.getByTestId('deactivate-btn-1'))
    await user.click(screen.getByTestId('confirm-cancel'))
    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument()
    // Only the initial listVendors call — no deactivate call
    expect(fetchSpy).toHaveBeenCalledTimes(1)
  })

  it('marks vendor inactive after confirmed deactivation', async () => {
    stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: { deactivated: true, devices_revoked: 1, sessions_invalidated: 1 } },
    ])
    const user = userEvent.setup()
    render(<MemoryRouter><VendorManagement /></MemoryRouter>)
    await waitFor(() => screen.getByTestId('deactivate-btn-1'))
    await user.click(screen.getByTestId('deactivate-btn-1'))
    await user.click(screen.getByTestId('confirm-ok'))
    await waitFor(() =>
      expect(screen.getByTestId('vendor-active-1')).toHaveTextContent('Inactive')
    )
  })
})
