import React, { useState } from 'react'
import '../../styles/design.css'

interface Props { title: string; value: string; onClose: () => void }

export default function CopyDialog({ title, value, onClose }: Props) {
  const [copied, setCopied] = useState(false)

  async function handleCopy() {
    try { await navigator.clipboard.writeText(value); setCopied(true) } catch {}
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label={title} data-testid="copy-dialog">
      <div className="modal">
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20 }}>
          <h3>{title}</h3>
          <button className="btn-icon" onClick={onClose} data-testid="copy-close">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
            </svg>
          </button>
        </div>
        <p style={{ fontSize: 13, color: '#8b8fa8', marginBottom: 14 }}>
          Copy this link and send it to the vendor. It expires in 24 hours and can only be used once.
        </p>
        <div style={{ display: 'flex', gap: 8, marginBottom: 20 }}>
          <input readOnly value={value} data-testid="copy-value"
            className="input" style={{ fontFamily: 'monospace', fontSize: 12 }}
            onFocus={e => e.target.select()} />
          <button className="btn btn-primary" onClick={handleCopy} data-testid="copy-btn" style={{ flexShrink: 0 }}>
            {copied ? '✓ Copied' : 'Copy'}
          </button>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end' }}>
          <button className="btn btn-ghost" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  )
}
