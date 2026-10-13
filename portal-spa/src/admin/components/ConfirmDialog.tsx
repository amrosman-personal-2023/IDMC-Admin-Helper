import React from 'react'
import '../../styles/design.css'

interface Props { message: string; onConfirm: () => void; onCancel: () => void }

export default function ConfirmDialog({ message, onConfirm, onCancel }: Props) {
  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" data-testid="confirm-dialog">
      <div className="modal">
        <div style={{ display: 'flex', gap: 14, marginBottom: 20 }}>
          <div style={{ width: 40, height: 40, borderRadius: 10, background: 'rgba(224,82,82,.12)', border: '1px solid rgba(224,82,82,.25)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#e05252" strokeWidth="2">
              <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
              <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
            </svg>
          </div>
          <div>
            <h3 style={{ marginBottom: 6 }}>Confirm action</h3>
            <p style={{ fontSize: 13, color: '#8b8fa8', lineHeight: 1.6 }}>{message}</p>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
          <button className="btn btn-ghost" onClick={onCancel} data-testid="confirm-cancel">Cancel</button>
          <button className="btn btn-danger" onClick={onConfirm} data-testid="confirm-ok">Confirm</button>
        </div>
      </div>
    </div>
  )
}
