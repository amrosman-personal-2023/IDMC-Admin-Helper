import React, { useEffect, useState, useCallback } from 'react'
import { getDashboard, DashboardStats } from '../api/endpoints'
import '../../styles/design.css'

const REFRESH_MS = 30_000

function StatCard({ label, value, color }: { label: string; value: number; color: string }) {
  return (
    <div style={{ background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 12, padding: '20px 24px' }}>
      <div style={{ fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.5px', color: '#8b8fa8', marginBottom: 10 }}>{label}</div>
      <div style={{ fontSize: 32, fontWeight: 800, color, fontVariantNumeric: 'tabular-nums' }}>{value.toLocaleString()}</div>
    </div>
  )
}

export default function Dashboard() {
  const [stats, setStats] = useState<DashboardStats | null>(null)
  const [error, setError] = useState('')
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try { setStats(await getDashboard()); setError(''); setLastRefresh(new Date()) }
    catch { setError('Failed to load dashboard data') }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => clearInterval(id)
  }, [load])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2>Dashboard</h2>
          <p style={{ color: '#8b8fa8', fontSize: 13, marginTop: 4 }}>Platform overview — auto-refreshes every 30 seconds</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {lastRefresh && <span style={{ fontSize: 12, color: '#5a5e78' }}>Updated {lastRefresh.toLocaleTimeString()}</span>}
          <button className="btn btn-ghost btn-sm" onClick={load}>Refresh</button>
        </div>
      </div>

      {error && <p className="alert alert-error">{error}</p>}

      {stats && (
        <>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 16 }}>
            <StatCard label="Active Vendors"     value={stats.active_vendors}     color="#4f7eff" />
            <StatCard label="Enrolled Devices"   value={stats.enrolled_devices}   color="#3ecf8e" />
            <StatCard label="Active Sessions"    value={stats.active_sessions}    color="#f5a623" />
            <StatCard label="Audit Events (24h)" value={stats.audit_events_24h}   color="#8b8fa8" />
          </div>

          <div style={{ background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 12, overflow: 'hidden' }}>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid #2e3150', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3>Recent Audit Events</h3>
              <span style={{ fontSize: 12, color: '#5a5e78' }}>Last 20 events</span>
            </div>
            <div style={{ overflowX: 'auto' }}>
              <table data-testid="recent-audit-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
                <thead>
                  <tr style={{ background: '#222539' }}>
                    <th style={th}>Timestamp</th>
                    <th style={th}>Event</th>
                    <th style={th}>Vendor</th>
                    <th style={th}>Source IP</th>
                  </tr>
                </thead>
                <tbody>
                  {stats.recent_audit.length === 0 && (
                    <tr><td colSpan={4} style={{ padding: '20px', textAlign: 'center', color: '#5a5e78' }}>No recent events</td></tr>
                  )}
                  {stats.recent_audit.map(r => (
                    <tr key={r.id} style={{ borderTop: '1px solid #2e3150' }}>
                      <td style={td}><span style={{ fontFamily: 'monospace', color: '#8b8fa8' }}>{r.timestamp.replace('T', ' ').slice(0, 19)}</span></td>
                      <td style={td}><EventBadge type={r.event_type} /></td>
                      <td style={td}>{r.vendor_id ?? <span style={{ color: '#5a5e78' }}>—</span>}</td>
                      <td style={td}><span style={{ fontFamily: 'monospace', color: '#8b8fa8', fontSize: 12 }}>{r.source_ip ?? '—'}</span></td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

function EventBadge({ type }: { type: string }) {
  const map: Record<string, string> = {
    vendor_login_success: 'badge-green', vendor_login_failure: 'badge-red',
    admin_login_success: 'badge-blue',  admin_login_failure: 'badge-red',
    file_upload: 'badge-blue', script_execution: 'badge-yellow',
    device_revocation: 'badge-red', enrollment: 'badge-green',
    vendor_deactivation: 'badge-red', force_expire_session: 'badge-yellow',
  }
  return <span className={`badge ${map[type] ?? 'badge-muted'}`}>{type.replace(/_/g, ' ')}</span>
}

const th: React.CSSProperties = { padding: '10px 16px', textAlign: 'left', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.5px', color: '#8b8fa8' }
const td: React.CSSProperties = { padding: '10px 16px', color: '#e8eaf6' }
