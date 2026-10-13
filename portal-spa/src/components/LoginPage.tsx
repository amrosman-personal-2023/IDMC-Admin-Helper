import React, { useState, useId } from 'react'
import { useNavigate, useSearchParams, Link } from 'react-router-dom'
import { login } from '../api/auth'
import { ApiError } from '../api/client'
import { safeRedirectTarget } from '../utils/redirect'
import '../styles/design.css'

const TOTP_REGEX = /^\d{6}$/
const MAX_TOTP_FAILURES = 3
const LOCKOUT_SECONDS = 60
// No device UUID needed — Google Authenticator enrollment uses a fixed placeholder

export default function LoginPage() {
  const navigate = useNavigate()
  const [params] = useSearchParams()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [totpCode, setTotpCode] = useState('')
  const [stage, setStage] = useState<'credentials' | 'totp'>('credentials')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)
  const [totpFailures, setTotpFailures] = useState(0)
  const [lockoutSecondsLeft, setLockoutSecondsLeft] = useState(0)
  const usernameId = useId()
  const passwordId = useId()
  const totpId = useId()
  const locked = lockoutSecondsLeft > 0

  function startLockout() {
    setLockoutSecondsLeft(LOCKOUT_SECONDS)
    const h = setInterval(() => setLockoutSecondsLeft(s => {
      if (s <= 1) { clearInterval(h); return 0 }
      return s - 1
    }), 1000)
  }

  async function handleCredentialsSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const resp = await login(username, password, '', '')
      if (resp.totp_required) {
        // Password was correct — server is asking for the TOTP code now
        setStage('totp')
      } else {
        // Shouldn't happen (no enrolled device would still require TOTP),
        // but handle gracefully: if a full token was returned, navigate
        navigate(safeRedirectTarget(params.get('next')))
      }
    } catch {
      setError('Login failed')
    } finally { setLoading(false) }
  }

  async function handleTotpSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!TOTP_REGEX.test(totpCode)) { setError('Enter a 6-digit code'); return }
    if (locked) return
    setError('')
    setLoading(true)
    try {
      await login(username, password, totpCode, '')
      navigate(safeRedirectTarget(params.get('next')))
    } catch {
      const f = totpFailures + 1
      setTotpFailures(f)
      setError('Login failed')
      setTotpCode('')
      if (f >= MAX_TOTP_FAILURES) startLockout()
    } finally { setLoading(false) }
  }

  return (
    <div style={s.root}>
      <div style={s.bgGrid} />
      <div style={s.box}>
        {/* Logo */}
        <div style={s.logoRow}>
          <svg width="28" height="28" viewBox="0 0 36 36" fill="none">
            <rect width="36" height="36" rx="10" fill="#4f7eff" fillOpacity=".15"/>
            <path d="M10 18 L18 10 L26 18 L18 26 Z" stroke="#4f7eff" strokeWidth="2" fill="none"/>
            <circle cx="18" cy="18" r="3" fill="#4f7eff"/>
          </svg>
          <span style={s.logoText}>IDMC Vendor Portal</span>
        </div>

        <h2 style={s.title}>
          {stage === 'credentials' ? 'Sign in to your account' : 'Two-factor verification'}
        </h2>
        <p style={s.sub}>
          {stage === 'credentials'
            ? 'Enter your vendor credentials to continue.'
            : 'Enter the 6-digit code from your authenticator app.'}
        </p>

        {stage === 'credentials' && (
          <form onSubmit={handleCredentialsSubmit} aria-label="Login form" style={s.form}>
            <div className="field">
              <label htmlFor={usernameId}>Username</label>
              <input id={usernameId} className="input" type="text" autoComplete="username"
                value={username} onChange={e => setUsername(e.target.value)} required disabled={loading} />
            </div>
            <div className="field">
              <label htmlFor={passwordId}>Password</label>
              <input id={passwordId} className="input" type="password" autoComplete="current-password"
                value={password} onChange={e => setPassword(e.target.value)} required disabled={loading} />
            </div>
            {error && <p className="alert alert-error" role="alert" data-testid="login-error">{error}</p>}
            <button className="btn btn-primary" type="submit" disabled={loading} style={s.submitBtn}>
              {loading ? 'Signing in…' : 'Continue'}
            </button>
          </form>
        )}

        {stage === 'totp' && (
          <form onSubmit={handleTotpSubmit} aria-label="TOTP form" noValidate style={s.form}>
            <div className="field">
              <label htmlFor={totpId}>Authentication code</label>
              <input id={totpId} className="input" type="text" inputMode="numeric"
                pattern="\d{6}" maxLength={6} autoComplete="one-time-code"
                value={totpCode} onChange={e => setTotpCode(e.target.value.replace(/\D/g, ''))}
                required disabled={loading || locked} data-testid="totp-input"
                style={{ fontSize: 24, letterSpacing: 8, textAlign: 'center' }} />
            </div>
            {error && <p className="alert alert-error" role="alert" data-testid="login-error">{error}</p>}
            {locked && (
              <p className="alert alert-error" role="status" data-testid="lockout-message">
                Too many attempts. Try again in {lockoutSecondsLeft}s.
              </p>
            )}
            <button className="btn btn-primary" type="submit" disabled={loading || locked} style={s.submitBtn}>
              {loading ? 'Verifying…' : 'Verify'}
            </button>
            <button type="button" style={s.backBtn} onClick={() => { setStage('credentials'); setError('') }}>
              ← Back
            </button>
          </form>
        )}

        <div style={s.footer}>
          <Link to="/">← Back to portal selection</Link>
        </div>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f1117', position: 'relative' },
  bgGrid: { position: 'absolute', inset: 0, opacity: .04, backgroundImage: 'linear-gradient(#4f7eff 1px, transparent 1px), linear-gradient(90deg, #4f7eff 1px, transparent 1px)', backgroundSize: '40px 40px', pointerEvents: 'none' },
  box: { position: 'relative', zIndex: 1, width: '100%', maxWidth: 400, background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 16, padding: 36, display: 'flex', flexDirection: 'column', gap: 20 },
  logoRow: { display: 'flex', alignItems: 'center', gap: 10 },
  logoText: { fontWeight: 700, fontSize: 15, color: '#e8eaf6' },
  title: { fontSize: 20, fontWeight: 700, color: '#e8eaf6', marginTop: 4 },
  sub: { fontSize: 13, color: '#8b8fa8', marginTop: -8 },
  form: { display: 'flex', flexDirection: 'column', gap: 16 },
  submitBtn: { width: '100%', justifyContent: 'center', padding: '10px 0', fontSize: 14 },
  backBtn: { background: 'none', border: 'none', color: '#8b8fa8', cursor: 'pointer', fontSize: 13, textAlign: 'left', padding: 0 },
  footer: { textAlign: 'center', fontSize: 12, borderTop: '1px solid #2e3150', paddingTop: 16 },
}
