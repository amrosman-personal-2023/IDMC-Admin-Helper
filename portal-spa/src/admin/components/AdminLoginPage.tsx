import React, { useState, useId } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { adminLogin } from '../api/endpoints'
import { AdminApiError } from '../api/client'
import { useAdminAuth } from '../context/AdminAuthContext'
import '../../styles/design.css'

const MAX_FAILURES = 5

export default function AdminLoginPage() {
  const navigate = useNavigate()
  const { refresh } = useAdminAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [failures, setFailures] = useState(0)
  const uid = useId(); const pid = useId()

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); setError(''); setLoading(true)
    try {
      await adminLogin(username, password)
      await refresh()
      navigate('/admin/dashboard', { replace: true })
    } catch {
      setFailures(f => f + 1); setError('Login failed')
    } finally { setLoading(false) }
  }

  return (
    <div style={s.root}>
      <div style={s.bgGrid} />
      <div style={s.box}>
        <div style={s.logoRow}>
          <div style={s.shield}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#3ecf8e" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <div style={s.logoText}>IDMC Admin Console</div>
            <div style={s.logoSub}>Internal access only</div>
          </div>
        </div>

        <div style={s.divider} />

        <h2 style={s.title}>Administrator sign in</h2>
        <p style={s.sub}>Password authentication — no TOTP required for admin accounts.</p>

        <form onSubmit={handleSubmit} aria-label="Admin login form" noValidate style={s.form}>
          <div className="field">
            <label htmlFor={uid}>Username</label>
            <input id={uid} className="input" type="text" autoComplete="username"
              value={username} onChange={e => setUsername(e.target.value)}
              required disabled={loading} data-testid="admin-username" />
          </div>
          <div className="field">
            <label htmlFor={pid}>Password</label>
            <input id={pid} className="input" type="password" autoComplete="current-password"
              value={password} onChange={e => setPassword(e.target.value)}
              required disabled={loading} data-testid="admin-password" />
          </div>
          {error && <p className="alert alert-error" role="alert" data-testid="admin-login-error">{error}</p>}
          {failures >= MAX_FAILURES && (
            <p className="alert alert-error" role="status" data-testid="lockout-warning">
              Multiple failed attempts detected. Please contact your system administrator.
            </p>
          )}
          <button className="btn btn-primary" type="submit" disabled={loading}
            style={{ width: '100%', justifyContent: 'center', padding: '10px 0', fontSize: 14 }}
            data-testid="admin-login-btn">
            {loading ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <div style={s.footer}>
          <Link to="/">← Back to portal selection</Link>
        </div>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f1117', position: 'relative' },
  bgGrid: { position: 'absolute', inset: 0, opacity: .03, backgroundImage: 'linear-gradient(#3ecf8e 1px, transparent 1px), linear-gradient(90deg, #3ecf8e 1px, transparent 1px)', backgroundSize: '40px 40px', pointerEvents: 'none' },
  box: { position: 'relative', zIndex: 1, width: '100%', maxWidth: 400, background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 16, padding: 36, display: 'flex', flexDirection: 'column', gap: 20 },
  logoRow: { display: 'flex', alignItems: 'center', gap: 14 },
  shield: { width: 42, height: 42, borderRadius: 12, background: 'rgba(62,207,142,.1)', border: '1px solid rgba(62,207,142,.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  logoText: { fontWeight: 700, fontSize: 15, color: '#e8eaf6' },
  logoSub: { fontSize: 11, color: '#5a5e78', marginTop: 1 },
  divider: { height: 1, background: '#2e3150' },
  title: { fontSize: 20, fontWeight: 700, color: '#e8eaf6' },
  sub: { fontSize: 13, color: '#8b8fa8', marginTop: -8 },
  form: { display: 'flex', flexDirection: 'column', gap: 16 },
  footer: { textAlign: 'center', fontSize: 12, borderTop: '1px solid #2e3150', paddingTop: 16 },
}
