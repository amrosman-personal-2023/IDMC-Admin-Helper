import React, { useEffect, useState, useCallback } from 'react'
import { listSessions, forceExpireSession, SessionRow } from '../api/endpoints'
import ConfirmDialog from './ConfirmDialog'
import '../../styles/design.css'

const REFRESH_MS = 15_000

export default function SessionOverview() {
  const [sessions, setSessions] = useState<SessionRow[]>([])
  const [loading, setLoading] = useState(true)
  const [confirmExpire, setConfirmExpire] = useState<number | null>(null)
  const [lastRefresh, setLastRefresh] = useState<Date | null>(null)

  const load = useCallback(async () => {
    try { setSessions(await listSessions()); setLastRefresh(new Date()) }
    catch {} finally { setLoading(false) }
  }, [])

  useEffect(() => {
    load()
    const id = setInterval(load, REFRESH_MS)
    return () => clearInterval(id)
  }, [load])

  async function handleExpire(id: number) {
    try { await forceExpireSession(id); setSessions(ss => ss.filter(s => s.id !== id)) }
    catch {} finally { setConfirmExpire(null) }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2>Active Sessions</h2>
          <p style={{ color: '#8b8fa8', fontSize: 13, marginTop: 4 }}>{sessions.length} active — auto-refreshes every 15 seconds</p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {lastRefresh && <span style={{ fontSize: 12, color: '#5a5e78' }}>Updated {lastRefresh.toLocaleTimeString()}</span>}
          <button className="btn btn-ghost btn-sm" onClick={load}>Refresh</button>
        </div>
      </div>

      <div style={{ background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 12, overflow: 'hidden' }}>
        <table data-testid="sessions-table" style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
          <thead>
            <tr style={{ background: '#222539' }}>
              {['ID','Subject','Role','Started','Last Active','Expires','Source IP','Actions'].map(h => (
                <th key={h} style={th}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {loading && <tr><td colSpan={8} style={{ padding: 20, textAlign: 'center', color: '#5a5e78' }}>Loading…</td></tr>}
            {!loading && sessions.length === 0 && <tr><td colSpan={8} style={{ padding: 20, textAlign: 'center', color: '#5a5e78' }}>No active sessions</td></tr>}
            {sessions.map(s => (
              <tr key={s.id} style={{ borderTop: '1px solid #2e3150' }} data-testid={`session-row-${s.id}`}>
                <td style={td}><span style={{ color: '#5a5e78', fontFamily: 'monospace' }}>#{s.id}</span></td>
                <td style={td}>
                  <span className={`badge ${s.subject_type === 'admin' ? 'badge-yellow' : 'badge-blue'}`}>
                    {s.subject_type}:{s.subject_id}
                  </span>
                </td>
                <td style={td}><span className="badge badge-muted">{s.role}</span></td>
                <td style={td}><span style={{ color: '#8b8fa8', fontFamily: 'monospace', fontSize: 12 }}>{s.created_at.slice(0, 19).replace('T',' ')}</span></td>
                <td style={td}><span style={{ color: '#8b8fa8', fontFamily: 'monospace', fontSize: 12 }}>{s.last_active_at.slice(0, 19).replace('T',' ')}</span></td>
                <td style={td}><span style={{ color: '#8b8fa8', fontFamily: 'monospace', fontSize: 12 }}>{s.expires_at.slice(0, 19).replace('T',' ')}</span></td>
                <td style={td}><span style={{ fontFamily: 'monospace', fontSize: 12 }}>{s.source_ip ?? '—'}</span></td>
                <td style={td}>
                  <button className="btn btn-danger btn-sm" onClick={() => setConfirmExpire(s.id)} data-testid={`expire-btn-${s.id}`}>
                    Force Expire
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {confirmExpire !== null && (
        <ConfirmDialog
          message={`Force-expire session #${confirmExpire}? The session will be terminated immediately.`}
          onConfirm={() => handleExpire(confirmExpire)}
          onCancel={() => setConfirmExpire(null)} />
      )}
    </div>
  )
}

const th: React.CSSProperties = { padding: '10px 16px', textAlign: 'left', fontWeight: 600, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.5px', color: '#8b8fa8' }
const td: React.CSSProperties = { padding: '10px 16px', color: '#e8eaf6' }
