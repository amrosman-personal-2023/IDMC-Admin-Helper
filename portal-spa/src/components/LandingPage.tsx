import React from 'react'
import { useNavigate } from 'react-router-dom'

export default function LandingPage() {
  const navigate = useNavigate()

  return (
    <div style={s.root}>
      {/* Background grid */}
      <div style={s.bgGrid} />

      <div style={s.container}>
        {/* Header */}
        <div style={s.header}>
          <div style={s.logo}>
            <svg width="36" height="36" viewBox="0 0 36 36" fill="none">
              <rect width="36" height="36" rx="10" fill="#4f7eff" fillOpacity=".15"/>
              <path d="M10 18 L18 10 L26 18 L18 26 Z" stroke="#4f7eff" strokeWidth="2" fill="none"/>
              <circle cx="18" cy="18" r="3" fill="#4f7eff"/>
            </svg>
            <span style={s.logoText}>IDMC Vendor Portal</span>
          </div>
          <span style={s.version}>v1.2</span>
        </div>

        {/* Hero */}
        <div style={s.hero}>
          <div style={s.heroBadge}>Informatica IDMC</div>
          <h1 style={s.heroTitle}>Secure File & Integration<br/>Management Portal</h1>
          <p style={s.heroSub}>
            Choose your portal to get started. Vendors access the external portal
            to upload files and trigger operations. Administrators access the
            internal console to manage vendors, devices, and audit activity.
          </p>
        </div>

        {/* Portal selection cards */}
        <div style={s.cards}>
          {/* Vendor portal */}
          <button style={s.card} onClick={() => navigate('/login')} className="portal-card">
            <div style={s.cardIcon}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#4f7eff" strokeWidth="1.5">
                <path d="M20 7H4a2 2 0 0 0-2 2v6a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V9a2 2 0 0 0-2-2z"/>
                <path d="M16 21V5a2 2 0 0 0-2-2h-4a2 2 0 0 0-2 2v16"/>
              </svg>
            </div>
            <div style={s.cardLabel}>External</div>
            <div style={s.cardTitle}>Vendor Portal</div>
            <div style={s.cardDesc}>
              Upload files to IDMC staging directories and trigger
              pre-approved integration scripts.
            </div>
            <ul style={s.cardFeatures}>
              <li>File upload with drag &amp; drop</li>
              <li>Script operation triggers</li>
              <li>TOTP two-factor authentication</li>
              <li>Session renewal with countdown</li>
            </ul>
            <div style={s.cardCta}>
              Sign in as Vendor
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
          </button>

          {/* Admin console */}
          <button style={{...s.card, ...s.cardAdmin}} onClick={() => navigate('/admin/login')} className="portal-card">
            <div style={{...s.cardIcon, ...s.cardIconAdmin}}>
              <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="#3ecf8e" strokeWidth="1.5">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/>
                <path d="m9 12 2 2 4-4"/>
              </svg>
            </div>
            <div style={{...s.cardLabel, ...s.cardLabelAdmin}}>Internal</div>
            <div style={s.cardTitle}>Admin Console</div>
            <div style={s.cardDesc}>
              Manage vendor accounts, device registry, audit logs, and
              active sessions across the platform.
            </div>
            <ul style={s.cardFeatures}>
              <li>Vendor &amp; device management</li>
              <li>Real-time session overview</li>
              <li>Searchable audit log + CSV export</li>
              <li>Enrollment link issuance</li>
            </ul>
            <div style={{...s.cardCta, ...s.cardCtaAdmin}}>
              Sign in as Admin
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M5 12h14M12 5l7 7-7 7"/>
              </svg>
            </div>
          </button>
        </div>

        {/* Footer */}
        <div style={s.footer}>
          <span>IDMC Vendor Portal · Classification: Internal — Restricted</span>
        </div>
      </div>

      <style>{`
        .portal-card { text-align: left; transition: transform 150ms ease, border-color 150ms ease, box-shadow 150ms ease; }
        .portal-card:hover { transform: translateY(-4px); box-shadow: 0 12px 40px rgba(0,0,0,.5); }
        .portal-card:hover { border-color: #4f7eff !important; }
        .portal-card:nth-child(2):hover { border-color: #3ecf8e !important; }
      `}</style>
    </div>
  )
}

const s: Record<string, React.CSSProperties> = {
  root: {
    minHeight: '100vh', background: '#0f1117',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    position: 'relative', overflow: 'hidden',
  },
  bgGrid: {
    position: 'absolute', inset: 0, opacity: .04,
    backgroundImage: 'linear-gradient(#4f7eff 1px, transparent 1px), linear-gradient(90deg, #4f7eff 1px, transparent 1px)',
    backgroundSize: '40px 40px',
    pointerEvents: 'none',
  },
  container: {
    position: 'relative', zIndex: 1,
    width: '100%', maxWidth: 960, padding: '40px 24px',
    display: 'flex', flexDirection: 'column', gap: 40,
  },
  header: { display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  logo: { display: 'flex', alignItems: 'center', gap: 12 },
  logoText: { fontSize: 18, fontWeight: 700, color: '#e8eaf6' },
  version: { fontSize: 12, color: '#5a5e78', background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 6, padding: '2px 8px' },

  hero: { textAlign: 'center', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 },
  heroBadge: { fontSize: 12, fontWeight: 600, color: '#4f7eff', background: 'rgba(79,126,255,.12)', border: '1px solid rgba(79,126,255,.25)', borderRadius: 99, padding: '4px 14px', letterSpacing: '.5px', textTransform: 'uppercase' },
  heroTitle: { fontSize: 'clamp(1.8rem, 4vw, 2.6rem)', fontWeight: 800, lineHeight: 1.2, color: '#e8eaf6', letterSpacing: '-.5px' },
  heroSub: { maxWidth: 560, fontSize: 15, color: '#8b8fa8', lineHeight: 1.7 },

  cards: { display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(380px, 1fr))', gap: 24 },
  card: {
    background: '#1a1d2e', border: '1px solid #2e3150', borderRadius: 16,
    padding: 32, cursor: 'pointer', display: 'flex', flexDirection: 'column', gap: 12,
    outline: 'none',
  },
  cardAdmin: {},
  cardIcon: { width: 56, height: 56, borderRadius: 14, background: 'rgba(79,126,255,.1)', border: '1px solid rgba(79,126,255,.2)', display: 'flex', alignItems: 'center', justifyContent: 'center' },
  cardIconAdmin: { background: 'rgba(62,207,142,.1)', border: '1px solid rgba(62,207,142,.2)' },
  cardLabel: { fontSize: 11, fontWeight: 700, letterSpacing: '.8px', textTransform: 'uppercase', color: '#4f7eff' },
  cardLabelAdmin: { color: '#3ecf8e' },
  cardTitle: { fontSize: 22, fontWeight: 700, color: '#e8eaf6' },
  cardDesc: { fontSize: 14, color: '#8b8fa8', lineHeight: 1.6 },
  cardFeatures: {
    listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 6,
    borderTop: '1px solid #2e3150', paddingTop: 16, marginTop: 4,
  },
  cardCta: { display: 'flex', alignItems: 'center', gap: 6, color: '#4f7eff', fontWeight: 600, fontSize: 14, marginTop: 8 },
  cardCtaAdmin: { color: '#3ecf8e' },
  footer: { textAlign: 'center', fontSize: 12, color: '#5a5e78' },
}
