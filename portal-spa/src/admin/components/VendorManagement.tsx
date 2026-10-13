import React, { useEffect, useState } from 'react'
import { listVendors, createVendor, deactivateVendor, VendorRow } from '../api/endpoints'
import ConfirmDialog from './ConfirmDialog'
import QrDialog from './QrDialog'
import '../../styles/design.css'

interface QrState { username: string; qrDataUri: string; otpauthUri: string }

export default function VendorManagement() {
  const [vendors, setVendors] = useState<VendorRow[]>([])
  const [loading, setLoading] = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [cUser, setCUser] = useState(''); const [cPass, setCPass] = useState(''); const [cRole, setCRole] = useState('vendor_standard')
  const [createErr, setCreateErr] = useState('')
  const [creating, setCreating] = useState(false)
  const [qrState, setQrState] = useState<QrState | null>(null)
  const [confirmDeactivate, setConfirmDeactivate] = useState<number | null>(null)

  async function load() {
    try { setVendors(await listVendors()) } catch {}
    finally { setLoading(false) }
  }
  useEffect(() => { load() }, [])

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault(); setCreateErr(''); setCreating(true)
    try {
      const r = await createVendor(cUser, cPass, cRole)
      setQrState({ username: r.username, qrDataUri: r.qr_data_uri, otpauthUri: r.otpauth_uri })
      setCUser(''); setCPass(''); setShowCreate(false)
      await load()
    } catch { setCreateErr('Failed to create vendor') }
    finally { setCreating(false) }
  }

  async function handleDeactivate(id: number) {
    try {
      await deactivateVendor(id)
      setVendors(vs => vs.map(v => v.id === id ? { ...v, active: false } : v))
    } catch {} finally { setConfirmDeactivate(null) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2>Vendor Management</h2>
          <p style={{ color: '#8b8fa8', fontSize: 13, marginTop: 4 }}>{vendors.length} vendor{vendors.length !== 1 ? 's' : ''} registered</p>
        </div>
        <button className="btn btn-primary" onClick={() => setShowCreate(s => !s)} data-testid="show-create-btn">
          {showCreate ? 'Cancel' : '+ Create Vendor'}
        </button>
      </div>

      {showCreate && (
        <div style={{ background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 12, padding: 24 }}>
          <h3 style={{ marginBottom: 16 }}>New Vendor Account</h3>
          <form onSubmit={handleCreate} aria-label="Create vendor form" data-testid="create-vendor-form"
            style={{ display: 'grid', gridTemplateColumns: '1fr 1fr auto auto', gap: 12, alignItems: 'end' }}>
            <div className="field">
              <label>Username</label>
              <input className="input" placeholder="vendor_username" value={cUser}
                onChange={e => setCUser(e.target.value)} required data-testid="create-username" />
            </div>
            <div className="field">
              <label>Password</label>
              <input className="input" type="password" placeholder="••••••••" value={cPass}
                onChange={e => setCPass(e.target.value)} required data-testid="create-password" />
            </div>
            <div className="field">
              <label>Role</label>
              <select className="select" value={cRole} onChange={e => setCRole(e.target.value)} data-testid="create-role">
                <option value="vendor_standard">Standard</option>
                <option value="vendor_premium">Premium</option>
              </select>
            </div>
            <button className="btn btn-primary" type="submit" disabled={creating} data-testid="create-submit">
              {creating ? 'Creating…' : 'Create'}
            </button>
          </form>
          {createErr && <p className="alert alert-error" style={{ marginTop: 12 }}>{createErr}</p>}
        </div>
      )}

      {qrState && (
        <QrDialog username={qrState.username} qrDataUri={qrState.qrDataUri}
          otpauthUri={qrState.otpauthUri} onClose={() => setQrState(null)} />
      )}

      <div style={{ background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 12, overflow: 'hidden' }}>
        <table data-testid="vendors-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#222539' }}>
              {['ID','Username','Role','Created','Status','Devices','Actions'].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={7} style={{ padding: 20, textAlign: 'center', color: '#5a5e78' }}>Loading…</td></tr>}
            {!loading && vendors.length === 0 && <tr><td colSpan={7} style={{ padding: 20, textAlign: 'center', color: '#5a5e78' }}>No vendors yet</td></tr>}
            {vendors.map(v => (
              <tr key={v.id} style={{ borderTop: '1px solid #2e3150' }} data-testid={`vendor-row-${v.id}`}>
                <td style={td}><span style={{ color: '#5a5e78', fontFamily: 'monospace' }}>#{v.id}</span></td>
                <td style={td}><span style={{ fontWeight: 600 }}>{v.username}</span></td>
                <td style={td}><span className={`badge ${v.role === 'vendor_premium' ? 'badge-blue' : 'badge-muted'}`}>{v.role.replace('vendor_', '')}</span></td>
                <td style={td}><span style={{ color: '#8b8fa8', fontFamily: 'monospace', fontSize: 12 }}>{v.created_at.slice(0, 10)}</span></td>
                <td style={td} data-testid={`vendor-active-${v.id}`}>
                  <span className={`badge ${v.active ? 'badge-green' : 'badge-red'}`}>{v.active ? 'Active' : 'Inactive'}</span>
                </td>
                <td style={td}>{v.device_count}</td>
                <td style={td}>
                  {v.active && (
                    <button className="btn btn-danger btn-sm" onClick={() => setConfirmDeactivate(v.id)} data-testid={`deactivate-btn-${v.id}`}>
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {confirmDeactivate !== null && (
        <ConfirmDialog
          message={`Deactivate vendor #${confirmDeactivate}? All associated devices will be revoked and active sessions terminated immediately.`}
          onConfirm={() => handleDeactivate(confirmDeactivate)}
          onCancel={() => setConfirmDeactivate(null)} />
      )}
    </div>
  )
}

const th: React.CSSProperties = { padding: '10px 16px', textAlign: 'left', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.5px', color: '#8b8fa8' }
const td: React.CSSProperties = { padding: '10px 16px', color: '#e8eaf6' }
