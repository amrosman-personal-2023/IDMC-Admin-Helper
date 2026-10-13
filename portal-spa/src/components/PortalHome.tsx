import React, { useEffect, useState } from 'react'
import { useNavigate, NavLink, Outlet, Routes, Route } from 'react-router-dom'
import { logout } from '../api/auth'
import { getAllowedConfig, AllowedConfig } from '../api/backend'
import { useSession } from '../hooks/useSession'
import SessionHeader from './SessionHeader'
import FileUploadView from './FileUploadView'
import ScriptOperationsView from './ScriptOperationsView'
import '../styles/design.css'

export default function PortalHome() {
  const navigate = useNavigate()
  const { session, secondsLeft, showRenewalBanner, dismissRenewalBanner, updateExpiry } = useSession()
  const [config, setConfig] = useState<AllowedConfig | null>(null)
  const [activeView, setActiveView] = useState<'upload' | 'operations'>('upload')

  useEffect(() => {
    if (!session.loading && !session.authenticated) { navigate('/login'); return }
    if (session.authenticated) getAllowedConfig().then(setConfig).catch(() => {})
  }, [session.loading, session.authenticated, navigate])

  async function handleLogout() {
    try { await logout() } catch {}
    navigate('/login')
  }

  if (session.loading) return (
    <div style={{ minHeight: '100vh', display: 'flex', alignItems: 'center', justifyContent: 'center', background: '#0f1117' }}>
      <span style={{ color: '#8b8fa8' }}>Loading…</span>
    </div>
  )

  return (
    <div style={s.root}>
      <SessionHeader secondsLeft={secondsLeft} showRenewalBanner={showRenewalBanner}
        onDismiss={dismissRenewalBanner} onRenewed={updateExpiry} />

      <div style={s.body}>
        {/* Sidebar */}
        <aside style={s.sidebar}>
          <div style={s.sidebarTop}>
            <div style={s.roleChip}>
              <span style={s.roleDot} />
              {session.role ?? 'vendor'}
            </div>
          </div>

          <nav style={s.nav}>
            <button style={{ ...s.navItem, ...(activeView === 'upload' ? s.navItemActive : {}) }}
              onClick={() => setActiveView('upload')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/>
                <polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/>
              </svg>
              File Upload
            </button>
            <button style={{ ...s.navItem, ...(activeView === 'operations' ? s.navItemActive : {}) }}
              onClick={() => setActiveView('operations')}>
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <polygon points="5 3 19 12 5 21 5 3"/>
              </svg>
              Script Operations
            </button>
          </nav>

          <div style={s.sidebarBottom}>
            <button style={s.logoutBtn} onClick={handleLogout}>
              <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
                <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
              </svg>
              Log out
            </button>
          </div>
        </aside>

        {/* Main content */}
        <main style={s.main}>
          {config === null && (
            <div style={{ color: '#8b8fa8', padding: 32 }}>Loading portal configuration…</div>
          )}
          {config && activeView === 'upload' && <FileUploadView directories={config.directories} />}
          {config && activeView === 'operations' && <ScriptOperationsView operations={config.operations} />}
        </main>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', flexDirection: 'column', height: '100vh', background: '#0f1117' },
  body: { display: 'flex', flex: 1, overflow: 'hidden' },
  sidebar: { width: 220, background: '#1a1d2e', borderRight: '1px solid #2e3150', display: 'flex', flexDirection: 'column', padding: '20px 12px', flexShrink: 0 },
  sidebarTop: { marginBottom: 24 },
  roleChip: { display: 'flex', alignItems: 'center', gap: 8, fontSize: 12, fontWeight: 600, color: '#8b8fa8', textTransform: 'uppercase', letterSpacing: '.4px' },
  roleDot: { width: 7, height: 7, borderRadius: '50%', background: '#3ecf8e' },
  nav: { display: 'flex', flexDirection: 'column', gap: 4, flex: 1 },
  navItem: { display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 8, background: 'none', border: 'none', color: '#8b8fa8', fontSize: 13, fontWeight: 500, cursor: 'pointer', textAlign: 'left', transition: 'background 150ms, color 150ms' },
  navItemActive: { background: 'rgba(79,126,255,.12)', color: '#4f7eff' },
  sidebarBottom: { paddingTop: 12, borderTop: '1px solid #2e3150' },
  logoutBtn: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'none', border: 'none', color: '#8b8fa8', fontSize: 13, cursor: 'pointer', borderRadius: 8, width: '100%', transition: 'color 150ms' },
  main: { flex: 1, overflow: 'auto', padding: 32 },
}
