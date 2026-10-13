import React, { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import {
  listDevices, revokeDevice, reissueEnrollmentLink,
  DeviceRow, listVendors, VendorRow,
} from '../api/endpoints'
import ConfirmDialog from './ConfirmDialog'
import QrDialog from './QrDialog'

interface Props { vendorId?: number }

export default function DeviceRegistry({ vendorId: propVendorId }: Props) {
  const params = useParams<{ id: string }>()
  const resolvedVendorId = propVendorId ?? (params.id ? Number(params.id) : undefined)

  const [devices, setDevices] = useState<DeviceRow[]>([])
  const [vendors, setVendors] = useState<VendorRow[]>([])
  const [filterVendorId, setFilterVendorId] = useState<string>(
    resolvedVendorId != null ? String(resolvedVendorId) : ''
  )
  const [loading, setLoading] = useState(true)
  const [confirmRevoke, setConfirmRevoke] = useState<DeviceRow | null>(null)
  const [qrState, setQrState] = useState<{ username: string; qrDataUri: string; otpauthUri: string } | null>(null)

  async function load(vid?: number) {
    setLoading(true)
    try { setDevices(await listDevices(vid)) }
    catch { /* stale data */ }
    finally { setLoading(false) }
  }

  useEffect(() => {
    listVendors().then(setVendors).catch(() => {})
    load(resolvedVendorId)
  }, [resolvedVendorId])

  function handleFilterChange(e: React.ChangeEvent<HTMLSelectElement>) {
    const v = e.target.value
    setFilterVendorId(v)
    load(v ? Number(v) : undefined)
  }

  async function handleRevoke(device: DeviceRow) {
    try {
      await revokeDevice(device.uuid_hash_suffix, device.vendor_id)
      setDevices(ds => ds.map(d => d.id === device.id ? { ...d, revoked: true } : d))
    } catch { /* ignore */ }
    finally { setConfirmRevoke(null) }
  }

  async function handleReissue(vendorId: number) {
    try {
      const resp = await reissueEnrollmentLink(vendorId)
      const v = vendors.find(v => v.id === vendorId)
      setQrState({ username: v?.username ?? String(vendorId), qrDataUri: resp.qr_data_uri, otpauthUri: resp.otpauth_uri })
      // Refresh devices table to show newly enrolled device
      await load(resolvedVendorId)
    } catch { /* ignore */ }
  }

  return (
    <section>
      <h2>Device Registry</h2>

      {resolvedVendorId == null && (
        <select value={filterVendorId} onChange={handleFilterChange}
          aria-label="Filter by vendor" data-testid="vendor-filter">
          <option value="">All vendors</option>
          {vendors.map(v => (
            <option key={v.id} value={v.id}>{v.username}</option>
          ))}
        </select>
      )}

      {loading && <p>Loading…</p>}

      <table data-testid="devices-table">
        <thead>
          <tr><th>Vendor</th><th>UUID (last 8)</th><th>Enrolled</th><th>Last Used</th><th>Status</th><th>Actions</th></tr>
        </thead>
        <tbody>
          {devices.map(d => (
            <tr key={d.id} data-testid={`device-row-${d.id}`}>
              <td>{d.vendor_id}</td>
              <td>{d.uuid_hash_suffix}</td>
              <td>{d.enrolled_at}</td>
              <td>{d.last_used_at ?? '—'}</td>
              <td data-testid={`device-status-${d.id}`}>{d.revoked ? 'Revoked' : 'Active'}</td>
              <td>
                {!d.revoked && (
                  <button onClick={() => setConfirmRevoke(d)}
                    data-testid={`revoke-btn-${d.id}`}>Revoke</button>
                )}
                <button onClick={() => handleReissue(d.vendor_id)}
                  data-testid={`reissue-btn-${d.id}`}>Re-issue link</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      {confirmRevoke && (
        <ConfirmDialog
          message={`Revoke device ${confirmRevoke.uuid_hash_suffix}?`}
          onConfirm={() => handleRevoke(confirmRevoke)}
          onCancel={() => setConfirmRevoke(null)}
        />
      )}

      {qrState && (
        <QrDialog username={qrState.username} qrDataUri={qrState.qrDataUri}
          otpauthUri={qrState.otpauthUri} onClose={() => setQrState(null)} />
      )}
    </section>
  )
}
