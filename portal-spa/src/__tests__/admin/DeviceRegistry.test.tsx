import React from 'react'
import { screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { MemoryRouter } from 'react-router-dom'
import { render } from '@testing-library/react'
import DeviceRegistry from '../../admin/components/DeviceRegistry'
import { stubFetch } from './helpers'

beforeEach(() => { vi.restoreAllMocks(); vi.useRealTimers() })

const DEVICES = [
  { id: 1, vendor_id: 1, uuid_hash_suffix: 'abcd1234', enrolled_at: '2026-01-01', revoked: false, revoked_at: null, last_used_at: '2026-01-02' },
  { id: 2, vendor_id: 1, uuid_hash_suffix: 'efgh5678', enrolled_at: '2026-01-01', revoked: true, revoked_at: '2026-01-03', last_used_at: null },
]
const VENDORS = [{ id: 1, username: 'acme', role: 'vendor_standard', created_at: '2026-01-01', active: true, device_count: 2 }]

function renderRegistry(vendorId?: number) {
  stubFetch([
    { ok: true, status: 200, json: VENDORS },
    { ok: true, status: 200, json: DEVICES },
  ])
  return render(
    <MemoryRouter initialEntries={[vendorId ? `/admin/vendors/${vendorId}/devices` : '/admin/devices']}>
      <DeviceRegistry vendorId={vendorId} />
    </MemoryRouter>
  )
}

// ── Device table ───────────────────────────────────────────────────────────

describe('device table', () => {
  it('renders device rows with status', async () => {
    renderRegistry(1)
    await waitFor(() => screen.getByTestId('device-row-1'))
    expect(screen.getByTestId('device-status-1')).toHaveTextContent('Active')
    expect(screen.getByTestId('device-status-2')).toHaveTextContent('Revoked')
  })

  it('does not show revoke button for already-revoked device', async () => {
    renderRegistry(1)
    await waitFor(() => screen.getByTestId('device-row-2'))
    expect(screen.queryByTestId('revoke-btn-2')).not.toBeInTheDocument()
  })
})

// ── Revoke device ──────────────────────────────────────────────────────────

describe('revoke device', () => {
  it('shows confirmation dialog before revoking', async () => {
    renderRegistry(1)
    await waitFor(() => screen.getByTestId('revoke-btn-1'))
    await userEvent.click(screen.getByTestId('revoke-btn-1'))
    expect(screen.getByTestId('confirm-dialog')).toBeInTheDocument()
  })

  it('marks device as revoked after confirmation', async () => {
    stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: DEVICES },
      { ok: true, status: 200, json: { revoked: true } },
    ])
    const user = userEvent.setup()
    render(<MemoryRouter><DeviceRegistry vendorId={1} /></MemoryRouter>)
    await waitFor(() => screen.getByTestId('revoke-btn-1'))
    await user.click(screen.getByTestId('revoke-btn-1'))
    await user.click(screen.getByTestId('confirm-ok'))
    await waitFor(() =>
      expect(screen.getByTestId('device-status-1')).toHaveTextContent('Revoked')
    )
  })

  it('does not revoke if user cancels', async () => {
    const fetchSpy = stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: DEVICES },
    ])
    const user = userEvent.setup()
    render(<MemoryRouter><DeviceRegistry vendorId={1} /></MemoryRouter>)
    await waitFor(() => screen.getByTestId('revoke-btn-1'))
    await user.click(screen.getByTestId('revoke-btn-1'))
    await user.click(screen.getByTestId('confirm-cancel'))
    expect(screen.queryByTestId('confirm-dialog')).not.toBeInTheDocument()
    expect(fetchSpy).toHaveBeenCalledTimes(2) // vendors + devices, no revoke
  })
})

// ── Re-issue enrollment link ───────────────────────────────────────────────

describe('re-issue enrollment link', () => {
  it('shows copy dialog with new enrollment link', async () => {
    stubFetch([
      { ok: true, status: 200, json: VENDORS },
      { ok: true, status: 200, json: DEVICES },
      { ok: true, status: 200, json: {
        vendor_id: 1,
        otpauth_uri: 'otpauth://totp/IDMC%20Portal:acme?secret=JBSWY3DPEHPK3PXP&issuer=IDMC+Portal',
        qr_data_uri: 'data:image/png;base64,ABC123',
      }},
      { ok: true, status: 200, json: DEVICES },  // reload after re-issue
    ])
    const user = userEvent.setup()
    render(<MemoryRouter><DeviceRegistry vendorId={1} /></MemoryRouter>)
    await waitFor(() => screen.getByTestId('reissue-btn-1'))
    await user.click(screen.getByTestId('reissue-btn-1'))
    await waitFor(() => expect(screen.getByTestId('qr-dialog')).toBeInTheDocument())
    expect(screen.getByTestId('qr-image')).toBeInTheDocument()
    expect(screen.getByTestId('copy-btn')).toBeInTheDocument()
  })
})
