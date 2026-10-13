import React, { useEffect, useState, useRef } from 'react'
import { getExtensions, updateExtensions } from '../api/endpoints'
import { AdminApiError } from '../api/client'
import '../../styles/design.css'

export default function ExtensionsManager() {
  const [extensions, setExtensions] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [newExt, setNewExt] = useState('')
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  async function load() {
    try {
      const data = await getExtensions()
      setExtensions(data.extensions)
    } catch {
      setError('Failed to load extensions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  function handleAdd() {
    setError(''); setSuccess('')
    let ext = newExt.trim().toLowerCase()
    if (!ext) return
    if (!ext.startsWith('.')) ext = '.' + ext
    if (!/^\.[a-z0-9]{1,16}$/.test(ext)) {
      setError('Extension must be a dot followed by 1–16 alphanumeric characters (e.g. .csv)')
      return
    }
    if (extensions.includes(ext)) {
      setError(`${ext} is already in the list`)
      return
    }
    setExtensions(prev => [...prev, ext].sort())
    setNewExt('')
    inputRef.current?.focus()
  }

  function handleRemove(ext: string) {
    setError(''); setSuccess('')
    setExtensions(prev => prev.filter(e => e !== ext))
  }

  async function handleSave() {
    if (extensions.length === 0) {
      setError('At least one extension is required')
      return
    }
    setError(''); setSuccess(''); setSaving(true)
    try {
      const data = await updateExtensions(extensions)
      setExtensions(data.extensions)
      setSuccess('Extensions saved successfully')
    } catch (err) {
      if (err instanceof AdminApiError && err.status === 422) {
        setError('One or more extensions are invalid')
      } else {
        setError('Failed to save extensions')
      }
    } finally {
      setSaving(false) }
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); handleAdd() }
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24, maxWidth: 700 }}>
      <div>
        <h2>Allowed File Extensions</h2>
        <p style={{ color: '#8b8fa8', fontSize: 13, marginTop: 4 }}>
          Control which file types vendors can upload. Changes take effect immediately —
          no service restart needed.
        </p>
      </div>

      {error   && <p className="alert alert-error"   role="alert">{error}</p>}
      {success && <p className="alert alert-success" role="status" data-testid="save-success">{success}</p>}

      {/* Add extension */}
      <div style={s.card}>
        <h3 style={{ marginBottom: 14 }}>Add extension</h3>
        <div style={{ display: 'flex', gap: 10 }}>
          <input
            ref={inputRef}
            className="input"
            type="text"
            placeholder=".parquet  or  parquet"
            value={newExt}
            onChange={e => setNewExt(e.target.value)}
            onKeyDown={handleKeyDown}
            data-testid="new-ext-input"
            style={{ maxWidth: 220 }}
          />
          <button className="btn btn-primary" onClick={handleAdd} data-testid="add-ext-btn">
            Add
          </button>
        </div>
        <p style={{ fontSize: 12, color: '#5a5e78', marginTop: 8 }}>
          Type with or without the leading dot — it will be added automatically.
        </p>
      </div>

      {/* Current list */}
      <div style={s.card}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
          <h3>{extensions.length} extension{extensions.length !== 1 ? 's' : ''} allowed</h3>
          <button
            className="btn btn-primary"
            onClick={handleSave}
            disabled={saving || loading}
            data-testid="save-btn"
          >
            {saving ? 'Saving…' : 'Save changes'}
          </button>
        </div>

        {loading && <p style={{ color: '#8b8fa8' }}>Loading…</p>}

        <div style={s.extGrid} data-testid="extensions-list">
          {extensions.map(ext => (
            <div key={ext} style={s.extChip} data-testid={`ext-chip-${ext}`}>
              <span style={s.extText}>{ext}</span>
              <button
                style={s.removeBtn}
                onClick={() => handleRemove(ext)}
                aria-label={`Remove ${ext}`}
                data-testid={`remove-${ext}`}
              >
                ×
              </button>
            </div>
          ))}
          {!loading && extensions.length === 0 && (
            <p style={{ color: '#e05252', fontSize: 13 }}>
              No extensions allowed — all uploads will be rejected.
            </p>
          )}
        </div>
      </div>

      {/* Info */}
      <div style={{ background: 'rgba(79,126,255,.06)', border: '1px solid rgba(79,126,255,.2)', borderRadius: 10, padding: '14px 18px', fontSize: 13, color: '#8b8fa8', lineHeight: 1.7 }}>
        <strong style={{ color: '#4f7eff' }}>Note:</strong> Changes are stored in memory only.
        If the backend API is restarted, the list resets to the defaults defined in the
        service configuration. To make changes permanent, update the{' '}
        <code style={{ background: '#222539', padding: '1px 6px', borderRadius: 4, color: '#e8eaf6' }}>
          ALLOWED_EXTENSIONS
        </code>{' '}
        in <code style={{ background: '#222539', padding: '1px 6px', borderRadius: 4, color: '#e8eaf6' }}>
          backend-api/app/config.py
        </code>.
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  card: {
    background: '#1a1d2e', border: '1px solid #2e3150',
    borderRadius: 12, padding: 24,
  },
  extGrid: {
    display: 'flex', flexWrap: 'wrap', gap: 8,
  },
  extChip: {
    display: 'inline-flex', alignItems: 'center', gap: 6,
    background: '#222539', border: '1px solid #2e3150',
    borderRadius: 6, padding: '5px 10px',
  },
  extText: {
    fontFamily: 'monospace', fontSize: 13, color: '#e8eaf6',
  },
  removeBtn: {
    background: 'none', border: 'none', cursor: 'pointer',
    color: '#5a5e78', fontSize: 16, lineHeight: 1,
    padding: '0 2px', borderRadius: 4,
    transition: 'color 150ms',
  },
}
