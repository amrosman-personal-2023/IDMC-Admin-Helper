import React from 'react'
import { renew } from '../api/auth'
import { ApiError } from '../api/client'
import '../styles/design.css'

interface Props {
  secondsLeft: number | null
  showRenewalBanner: boolean
  onDismiss: () => void
  onRenewed: (newExpiry: string) => void
}

function fmt(secs: number) {
  return `${Math.floor(secs / 60)}:${String(secs % 60).padStart(2, '0')}`
}

function urgency(secs: number | null) {
  if (secs === null) return '#8b8fa8'
  if (secs < 120) return '#e05252'
  if (secs < 300) return '#f5a623'
  return '#3ecf8e'
}

export default function SessionHeader({ secondsLeft, showRenewalBanner, onDismiss, onRenewed }: Props) {
  const [code, setCode] = React.useState('')
  const [err, setErr] = React.useState('')
  const [renewing, setRenewing] = React.useState(false)

  async function handleRenew(e: React.FormEvent) {
    e.preventDefault()
    if (!/^\d{6}$/.test(code)) { setErr('Enter a 6-digit code'); return }
    setRenewing(true); setErr('')
    try {
      const r = await renew(code)
      setCode(''); onRenewed(r.expires_at)
    } catch (e) {
      setErr(e instanceof ApiError && e.status === 401 ? 'Code rejected' : 'Renewal failed')
    } finally { setRenewing(false) }
  }

  return (
    <div style={s.root}>
      <div style={s.left}>
        <svg width="20" height="20" viewBox="0 0 36 36" fill="none">
          <path d="M10 18 L18 10 L26 18 L18 26 Z" stroke="#4f7eff" strokeWidth="2" fill="none"/>
          <circle cx="18" cy="18" r="3" fill="#4f7eff"/>
        </svg>
        <span style={s.brand}>IDMC Vendor Portal</span>
      </div>

      <div style={s.right}>
        {secondsLeft !== null && (
          <div style={{ ...s.timer, color: urgency(secondsLeft) }}
               data-testid="session-countdown" aria-live="polite">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/>
            </svg>
            {fmt(secondsLeft)}
          </div>
        )}
      </div>

      {showRenewalBanner && (
        <div style={s.banner} role="status" data-testid="renewal-banner">
          <div style={s.bannerContent}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f5a623" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
            <span>Session expiring in {secondsLeft !== null ? fmt(secondsLeft) : '—'}</span>
          </div>
          <form onSubmit={handleRenew} aria-label="Session renewal form" style={s.bannerForm}>
            <input className="input" type="text" inputMode="numeric" maxLength={6}
              placeholder="6-digit code" value={code}
              onChange={e => setCode(e.target.value.replace(/\D/g, ''))}
              data-testid="renewal-totp-input" disabled={renewing}
              style={{ width: 120, padding: '6px 10px', fontSize: 13 }} />
            <button className="btn btn-primary btn-sm" type="submit" disabled={renewing}>
              {renewing ? '…' : 'Renew'}
            </button>
            <button className="btn btn-ghost btn-sm" type="button" onClick={onDismiss}>Dismiss</button>
          </form>
          {err && <p role="alert" style={s.bannerErr}>{err}</p>}
        </div>
      )}
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { background: '#1a1d2e', borderBottom: '1px solid #2e3150', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 24px', height: 52, position: 'relative', flexShrink: 0 },
  left: { display: 'flex', alignItems: 'center', gap: 10 },
  brand: { fontWeight: 700, fontSize: 14, color: '#e8eaf6' },
  right: { display: 'flex', alignItems: 'center', gap: 16 },
  timer: { display: 'flex', alignItems: 'center', gap: 5, fontSize: 13, fontWeight: 600, fontVariantNumeric: 'tabular-nums' },
  banner: { position: 'absolute', top: 52, left: 0, right: 0, background: 'rgba(245,166,35,.08)', borderBottom: '1px solid rgba(245,166,35,.25)', padding: '10px 24px', display: 'flex', alignItems: 'center', gap: 16, flexWrap: 'wrap', zIndex: 10 },
  bannerContent: { display: 'flex', alignItems: 'center', gap: 8, color: '#f5a623', fontSize: 13, fontWeight: 500 },
  bannerForm: { display: 'flex', alignItems: 'center', gap: 8 },
  bannerErr: { color: '#f08080', fontSize: 12 },
}
