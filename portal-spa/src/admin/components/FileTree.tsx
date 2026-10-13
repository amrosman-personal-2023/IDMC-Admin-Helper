import React, { useEffect, useState } from 'react'
import { getLogTree, TreeEntry, LogRoot } from '../api/endpoints'
import '../../styles/design.css'

interface Props {
  onFileSelect: (path: string) => void
  selectedPath: string
}

interface Node {
  entry: TreeEntry
  children?: Node[]
  expanded: boolean
  loaded: boolean
}

interface RootNode {
  root: LogRoot
  children?: Node[]
  expanded: boolean
  loaded: boolean
}

function formatSize(bytes: number | null): string {
  if (bytes == null) return ''
  if (bytes < 1024) return `${bytes}B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`
  return `${(bytes / 1024 / 1024).toFixed(1)}MB`
}

function formatDate(ts: number): string {
  return new Date(ts * 1000).toLocaleDateString()
}

function FileIcon() {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" style={{ flexShrink: 0 }}>
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
    </svg>
  )
}

function DirIcon({ open }: { open: boolean }) {
  return (
    <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="#f5a623" strokeWidth="2" style={{ flexShrink: 0 }}>
      {open
        ? <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
        : <path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/>
      }
    </svg>
  )
}

export default function FileTree({ onFileSelect, selectedPath }: Props) {
  const [rootNodes, setRootNodes] = useState<RootNode[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    getLogTree().then(data => {
      if ('roots' in data) {
        setRootNodes(data.roots.map(r => ({ root: r, expanded: false, loaded: false })))
      }
    }).catch(() => setError('Failed to load log roots'))
  }, [])

  async function toggleRoot(rn: RootNode) {
    if (!rn.expanded && !rn.loaded) {
      try {
        const data = await getLogTree(rn.root.path)
        if ('entries' in data) {
          rn.children = data.entries.map(e => ({ entry: e, expanded: false, loaded: false }))
        } else {
          rn.children = []
        }
        rn.loaded = true
      } catch { rn.children = [] }
    }
    rn.expanded = !rn.expanded
    setRootNodes(r => [...r])
  }

  async function toggleDir(node: Node) {
    if (node.entry.type !== 'dir') return
    if (!node.expanded && !node.loaded) {
      try {
        const data = await getLogTree(node.entry.path)
        if ('entries' in data) {
          node.children = data.entries.map(e => ({ entry: e, expanded: false, loaded: false }))
        } else {
          node.children = []
        }
        node.loaded = true
      } catch { node.children = [] }
    }
    node.expanded = !node.expanded
    setRootNodes(r => [...r])
  }

  function renderNode(node: Node, depth: number): React.ReactNode {
    const isSelected = node.entry.path === selectedPath
    const isFile = node.entry.type === 'file'
    return (
      <div key={node.entry.path}>
        <div
          onClick={() => isFile ? onFileSelect(node.entry.path) : toggleDir(node)}
          title={`${node.entry.path}${node.entry.size_bytes != null ? ` (${formatSize(node.entry.size_bytes)})` : ''}`}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '4px 8px', paddingLeft: 8 + depth * 14,
            cursor: 'pointer', borderRadius: 4,
            background: isSelected ? 'rgba(79,126,255,.15)' : 'transparent',
            color: isSelected ? '#4f7eff' : isFile ? '#e8eaf6' : '#f5a623',
            fontSize: 12,
          }}
        >
          {isFile ? <FileIcon /> : <DirIcon open={node.expanded} />}
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {node.entry.name}
          </span>
          {isFile && node.entry.size_bytes != null && (
            <span style={{ color: '#5a5e78', fontSize: 11, flexShrink: 0 }}>
              {formatSize(node.entry.size_bytes)}
            </span>
          )}
        </div>
        {node.expanded && node.children && (
          <div>{node.children.map(child => renderNode(child, depth + 1))}</div>
        )}
      </div>
    )
  }

  function renderRootNode(rn: RootNode): React.ReactNode {
    return (
      <div key={rn.root.name}>
        <div
          onClick={() => toggleRoot(rn)}
          title={rn.root.path}
          style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '5px 8px',
            cursor: 'pointer', borderRadius: 4,
            color: '#f5a623', fontSize: 12, fontWeight: 600,
            background: 'transparent',
          }}
        >
          <DirIcon open={rn.expanded} />
          <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {rn.root.label}
          </span>
        </div>
        {rn.expanded && rn.children && (
          <div>{rn.children.map(child => renderNode(child, 1))}</div>
        )}
      </div>
    )
  }

  return (
    <div style={s.root}>
      <div style={s.header}>Files</div>
      {error && <p style={{ color: '#e05252', fontSize: 12, padding: 8 }}>{error}</p>}
      <div style={s.tree}>{rootNodes.map(rn => renderRootNode(rn))}</div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' },
  header: { padding: '10px 12px', fontSize: 11, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.5px', color: '#5a5e78', borderBottom: '1px solid #2e3150' },
  tree: { flex: 1, overflowY: 'auto', padding: '6px 4px' },
}
