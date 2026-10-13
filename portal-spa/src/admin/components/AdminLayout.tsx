import React from 'react'
import { NavLink, useNavigate, Outlet, useLocation } from 'react-router-dom'
import { adminLogout } from '../api/endpoints'
import { useAdminAuth } from '../context/AdminAuthContext'
import '../../styles/design.css'

const NAV = [
  { to: '/admin/dashboard', label: 'Dashboard', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
      <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
    </svg>
  )},
  { to: '/admin/vendors', label: 'Vendors', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
      <circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>
    </svg>
  )},
  { to: '/admin/devices', label: 'Devices', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="5" y="2" width="14" height="20" rx="2" ry="2"/>
      <line x1="12" y1="18" x2="12.01" y2="18"/>
    </svg>
  )},
  { to: '/admin/audit', label: 'Audit Log', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/><polyline points="10 9 9 9 8 9"/>
    </svg>
  )},
  { to: '/admin/sessions', label: 'Sessions', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>
    </svg>
  )},
  { to: '/admin/extensions', label: 'Extensions', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="16 18 22 12 16 6"/>
      <polyline points="8 6 2 12 8 18"/>
    </svg>
  )},
  { to: '/admin/logs', label: 'Log Analyser', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
      <polyline points="14 2 14 8 20 8"/>
      <line x1="16" y1="13" x2="8" y2="13"/>
      <line x1="16" y1="17" x2="8" y2="17"/>
    </svg>
  )},
  { to: '/admin/settings/llm', label: 'LLM Settings', icon: (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M12 2a10 10 0 1 0 10 10"/>
      <path d="M12 8v4l3 3"/>
      <circle cx="18" cy="6" r="3" fill="#4f7eff" stroke="none"/>
    </svg>
  )},
]

export default function AdminLayout() {
  const navigate = useNavigate()
  const location = useLocation()
  const { markLoggedOut } = useAdminAuth()

  async function handleLogout() {
    try { await adminLogout() } catch {}
    markLoggedOut()
    navigate('/admin/login', { replace: true })
  }

  return (
    <div style={s.root}>
      {/* Sidebar */}
      <aside style={s.sidebar}>
        <div style={s.sidebarHeader}>
          <div style={s.shield}>
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#3ecf8e" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
            </svg>
          </div>
          <div>
            <div style={s.brandName}>Admin Console</div>
            <div style={s.brandSub}>IDMC Portal</div>
          </div>
        </div>

        <div style={s.navDivider} />

        <nav style={s.nav}>
          {NAV.map(item => {
            const active = location.pathname.startsWith(item.to)
            return (
              <NavLink key={item.to} to={item.to}
                style={{ ...s.navItem, ...(active ? s.navActive : {}) }}>
                <span style={{ color: active ? '#3ecf8e' : 'inherit', display: 'flex' }}>{item.icon}</span>
                {item.label}
              </NavLink>
            )
          })}
        </nav>

        <div style={s.sidebarFooter}>
          <button style={s.logoutBtn} onClick={handleLogout} data-testid="admin-logout-btn">
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4"/>
              <polyline points="16 17 21 12 16 7"/><line x1="21" y1="12" x2="9" y2="12"/>
            </svg>
            Sign out
          </button>
        </div>
      </aside>

      {/* Content */}
      <div style={s.content}>
        {/* Top bar */}
        <header style={s.topbar}>
          <div style={s.breadcrumb}>
            {NAV.find(n => location.pathname.startsWith(n.to))?.label ?? 'Admin'}
          </div>
          <div style={s.adminBadge}>
            <span style={s.adminDot} />
            Administrator
          </div>
        </header>

        <main style={s.main}>
          {/* Log analyser needs full-height zero-padding; all other pages get padding */}
          {location.pathname.startsWith('/admin/logs')
            ? <Outlet />
            : <div style={{ flex: 1, overflow: 'auto', padding: 28 }}><Outlet /></div>
          }
        </main>
      </div>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: { display: 'flex', height: '100vh', background: '#0f1117', overflow: 'hidden' },
  sidebar: { width: 240, background: '#1a1d2e', borderRight: '1px solid #2e3150', display: 'flex', flexDirection: 'column', flexShrink: 0 },
  sidebarHeader: { display: 'flex', alignItems: 'center', gap: 12, padding: '20px 20px 16px' },
  shield: { width: 36, height: 36, borderRadius: 10, background: 'rgba(62,207,142,.1)', border: '1px solid rgba(62,207,142,.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  brandName: { fontWeight: 700, fontSize: 14, color: '#e8eaf6' },
  brandSub: { fontSize: 11, color: '#5a5e78' },
  navDivider: { height: 1, background: '#2e3150', margin: '0 12px 12px' },
  nav: { display: 'flex', flexDirection: 'column', gap: 2, padding: '0 8px', flex: 1 },
  navItem: { display: 'flex', alignItems: 'center', gap: 10, padding: '9px 12px', borderRadius: 8, color: '#8b8fa8', fontSize: 13, fontWeight: 500, textDecoration: 'none', transition: 'background 150ms, color 150ms' },
  navActive: { background: 'rgba(62,207,142,.08)', color: '#e8eaf6' },
  sidebarFooter: { padding: '12px 8px 20px', borderTop: '1px solid #2e3150', marginTop: 'auto' },
  logoutBtn: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 12px', background: 'none', border: 'none', color: '#8b8fa8', fontSize: 13, cursor: 'pointer', borderRadius: 8, width: '100%', transition: 'color 150ms, background 150ms' },
  content: { flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  topbar: { height: 52, background: '#1a1d2e', borderBottom: '1px solid #2e3150', display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '0 28px', flexShrink: 0 },
  breadcrumb: { fontSize: 14, fontWeight: 600, color: '#e8eaf6' },
  adminBadge: { display: 'flex', alignItems: 'center', gap: 7, fontSize: 12, color: '#8b8fa8' },
  adminDot: { width: 7, height: 7, borderRadius: '50%', background: '#3ecf8e' },
  main: { flex: 1, overflow: 'hidden', padding: 0, display: 'flex', flexDirection: 'column' },
}
