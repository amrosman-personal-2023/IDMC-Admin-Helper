import React, { useState } from 'react'
import '../../styles/design.css'

interface Props {
  username: string
  qrDataUri: string
  otpauthUri: string
  onClose: () => void
}

export default function QrDialog({ username, qrDataUri, otpauthUri, onClose }: Props) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try { await navigator.clipboard.writeText(otpauthUri); setCopied(true) } catch {}
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true"
      aria-label="Scan QR code" data-testid="qr-dialog">
      <div className="modal" style={{ maxWidth: 440 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3>Scan with Google Authenticator</h3>
          <button className="btn-icon" onClick={onClose} data-testid="qr-close">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>

        <p style={{ fontSize: 13, color: '#8b8fa8', marginBottom: 20, lineHeight: 1.6 }}>
          Have <strong style={{ color: '#e8eaf6' }}>{username}</strong> open Google Authenticator,
          tap <strong style={{ color: '#e8eaf6' }}>+</strong> → <strong style={{ color: '#e8eaf6' }}>Scan a QR code</strong>,
          then scan the code below. This QR code is shown once — store it securely.
        </p>

        {/* QR code */}
        <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 20 }}>
          <div style={{ background: '#fff', padding: 12, borderRadius: 10, display: 'inline-block' }}>
            <img src={qrDataUri} alt="TOTP QR code" width={200} height={200}
              data-testid="qr-image" style={{ display: 'block' }} />
          </div>
        </div>

        {/* Steps */}
        <div style={{ background: '#222539', borderRadius: 8, padding: '12px 16px', marginBottom: 20, fontSize: 13 }}>
          <div style={{ fontWeight: 600, color: '#8b8fa8', marginBottom: 8, fontSize: 11, textTransform: 'uppercase', letterSpacing: '.4px' }}>
            Setup steps
          </div>
          {['Open Google Authenticator on your phone',
            'Tap the + button → Scan a QR code',
            'Point your camera at the QR code above',
            'The account appears immediately — no further steps needed'
          ].map((step, i) => (
            <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 6, alignItems: 'flex-start' }}>
              <span style={{ width: 18, height: 18, borderRadius: '50%', background: 'rgba(62,207,142,.15)', color: '#3ecf8e', fontSize: 11, fontWeight: 700, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                {i + 1}
              </span>
              <span style={{ color: '#8b8fa8' }}>{step}</span>
            </div>
          ))}
        </div>

        {/* Manual entry fallback */}
        <details style={{ marginBottom: 20 }}>
          <summary style={{ fontSize: 12, color: '#5a5e78', cursor: 'pointer', userSelect: 'none' }}>
            Can't scan? Manual entry
          </summary>
          <div style={{ marginTop: 10, display: 'flex', gap: 8 }}>
            <input readOnly value={otpauthUri} className="input"
              style={{ fontFamily: 'monospace', fontSize: 11 }}
              data-testid="qr-uri" onFocus={e => e.target.select()} />
            <button className="btn btn-ghost btn-sm" onClick={handleCopy}
              data-testid="copy-btn" style={{ flexShrink: 0 }}>
              {copied ? '✓' : 'Copy'}
            </button>
          </div>
        </details>

        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-primary" onClick={onClose}>Done</button>
        </div>
      </div>
    </div>
  )
}
