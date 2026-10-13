import React, { useState, useMemo } from 'react'
import { LogFile } from '../api/endpoints'
import '../../styles/design.css'

interface Props {
  file: LogFile | null
  loading: boolean
  onAnalyse: () => void
  analysing: boolean
  sensitivityConfirmed: boolean
  onConfirmSensitivity: () => void
}

export default function LogViewer({
  file, loading, onAnalyse, analysing, sensitivityConfirmed, onConfirmSensitivity,
}: Props) {
  const [search, setSearch] = useState('')
  const [showWarning, setShowWarning] = useState(true)

  const lines = useMemo(() => {
    if (!file) return []
    return file.content.split('\n')
  }, [file])

  const filtered = useMemo(() => {
    if (!search.trim()) return lines.map((l, i) => ({ line: l, num: i + 1, match: false }))
    const q = search.toLowerCase()
    return lines.map((l, i) => ({ line: l, num: i + 1, match: l.toLowerCase().includes(q) }))
  }, [lines, search])

  const shown = search.trim() ? filtered.filter(l => l.match) : filtered

  if (loading) return (
    <div style={s.placeholder}>
      <span style={{ color: '#8b8fa8' }}>Loading file…</span>
    </div>
  )

  if (!file) return (
    <div style={s.placeholder}>
      <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#2e3150" strokeWidth="1.5">
        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
        <polyline points="14 2 14 8 20 8"/>
      </svg>
      <p style={{ color: '#5a5e78', marginTop: 12 }}>Select a file from the tree to view its contents</p>
    </div>
  )

  return (
    <div style={s.root}>
      {/* Header */}
      <div style={s.header}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, flex: 1, minWidth: 0 }}>
          <span style={{ fontWeight: 600, color: '#e8eaf6', fontSize: 13, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {file.path.split('/').pop()}
          </span>
          <span className="badge badge-blue">{file.service}</span>
          <span style={{ color: '#5a5e78', fontSize: 12 }}>{file.lines.toLocaleString()} lines</span>
          <span style={{ color: '#5a5e78', fontSize: 12 }}>{(file.size_bytes / 1024).toFixed(1)} KB</span>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          <input className="input" placeholder="Search…" value={search}
            onChange={e => setSearch(e.target.value)}
            style={{ width: 160, padding: '5px 10px', fontSize: 12 }} />
          <button className="btn btn-primary btn-sm" onClick={onAnalyse}
            disabled={analysing || (file.sensitive && !sensitivityConfirmed)}
            data-testid="analyse-btn">
            {analysing ? 'Analysing…' : '✦ Analyse with AI'}
          </button>
        </div>
      </div>

      {/* Sensitivity warning */}
      {file.sensitive && !sensitivityConfirmed && showWarning && (
        <div style={s.warning} data-testid="sensitivity-warning">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#f5a623" strokeWidth="2">
            <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/>
            <line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12.01" y2="17"/>
          </svg>
          <span style={{ flex: 1, fontSize: 13 }}>
            This file may contain <strong>sensitive data</strong> (passwords, tokens, API keys).
            Confirm before sending to an external AI provider.
          </span>
          <button className="btn btn-primary btn-sm" onClick={() => { onConfirmSensitivity(); setShowWarning(false) }}
            data-testid="confirm-sensitivity-btn">
            I understand — proceed
          </button>
          <button className="btn btn-ghost btn-sm" onClick={() => setShowWarning(false)}>Dismiss</button>
        </div>
      )}

      {/* Content */}
      <div style={s.content}>
        {search.trim() && (
          <div style={{ padding: '4px 12px', fontSize: 12, color: '#8b8fa8', borderBottom: '1px solid #2e3150' }}>
            {shown.length} matching line{shown.length !== 1 ? 's' : ''}
          </div>
        )}
        <div style={s.lines}>
          {shown.map(({ line, num, match }) => (
            <div key={num} style={{ display: 'flex', minHeight: 20 }}>
              <span style={s.lineNum}>{num}</span>
              <span style={{
                ...s.lineText,
                background: match ? 'rgba(245,166,35,.1)' : 'transparent',
                color: line.match(/error|fail|exception|critical/i) ? '#f08080'
                  : line.match(/warn/i) ? '#f5a623'
                  : '#c8ccd8',
              }}>
                {line || ' '}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' },
  placeholder: { flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center' },
  header: { display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', borderBottom: '1px solid #2e3150', background: '#1a1d2e', flexShrink: 0 },
  warning: { display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', background: 'rgba(245,166,35,.08)', borderBottom: '1px solid rgba(245,166,35,.25)', flexShrink: 0 },
  content: { flex: 1, overflowY: 'auto', background: '#0f1117' },
  lines: { fontFamily: 'monospace', fontSize: 12, lineHeight: 1.6 },
  lineNum: { minWidth: 48, padding: '0 10px', color: '#3a3e55', textAlign: 'right', userSelect: 'none', flexShrink: 0, borderRight: '1px solid #1a1d2e' },
  lineText: { padding: '0 12px', flex: 1, whiteSpace: 'pre-wrap', wordBreak: 'break-all' },
}
