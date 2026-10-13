import React, { useEffect, useState, useCallback } from 'react'
import { useSearchParams } from 'react-router-dom'
import { getAuditLog, exportAuditCsv, AuditRow, AuditFilters, listVendors, VendorRow } from '../api/endpoints'

const EVENT_TYPES = ['login', 'upload', 'script', 'revocation', 'enrollment', 'admin_action']

export default function AuditLogViewer() {
  const [searchParams, setSearchParams] = useSearchParams()
  const [rows, setRows] = useState<AuditRow[]>([])
  const [vendors, setVendors] = useState<VendorRow[]>([])
  const [page, setPage] = useState(Number(searchParams.get('page') ?? '1'))
  const [totalPages, setTotalPages] = useState(1)
  const [loading, setLoading] = useState(true)

  const filters: AuditFilters = {
    vendor_id: searchParams.get('vendor_id') ?? undefined,
    event_type: searchParams.get('event_type') ?? undefined,
    date_from: searchParams.get('date_from') ?? undefined,
    date_to: searchParams.get('date_to') ?? undefined,
    page,
    page_size: 50,
  }

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const resp = await getAuditLog(filters)
      setRows(resp.results)
      setTotalPages(Math.max(1, Math.ceil(resp.results.length / 50)))
    } catch { /* stale */ }
    finally { setLoading(false) }
  }, [searchParams, page])

  useEffect(() => { listVendors().then(setVendors).catch(() => {}) }, [])
  useEffect(() => { load() }, [load])

  function updateFilter(key: string, value: string) {
    const next = new URLSearchParams(searchParams)
    if (value) next.set(key, value); else next.delete(key)
    next.set('page', '1')
    setPage(1)
    setSearchParams(next)
  }

  async function handleExportCsv() {
    try {
      const resp = await exportAuditCsv(filters)
      const blob = await resp.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'audit_log.csv'
      a.click()
      URL.revokeObjectURL(url)
    } catch { /* ignore */ }
  }

  return (
    <section>
      <h2>Audit Log</h2>

      <div data-testid="audit-filters">
        <select value={filters.vendor_id ?? ''} aria-label="Filter by vendor"
          onChange={e => updateFilter('vendor_id', e.target.value)}
          data-testid="filter-vendor">
          <option value="">All vendors</option>
          {vendors.map(v => <option key={v.id} value={v.id}>{v.username}</option>)}
        </select>

        <select value={filters.event_type ?? ''} aria-label="Filter by event type"
          onChange={e => updateFilter('event_type', e.target.value)}
          data-testid="filter-event-type">
          <option value="">All event types</option>
          {EVENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>

        <input type="date" value={filters.date_from ?? ''} aria-label="Date from"
          onChange={e => updateFilter('date_from', e.target.value)}
          data-testid="filter-date-from" />

        <input type="date" value={filters.date_to ?? ''} aria-label="Date to"
          onChange={e => updateFilter('date_to', e.target.value)}
          data-testid="filter-date-to" />

        <button onClick={handleExportCsv} data-testid="export-csv-btn">Export CSV</button>
      </div>

      {loading && <p>Loading…</p>}

      <table data-testid="audit-table">
        <thead>
          <tr><th>Timestamp</th><th>Event</th><th>Subject</th><th>Vendor</th><th>Source IP</th><th>Detail</th></tr>
        </thead>
        <tbody>
          {rows.map(r => (
            <tr key={r.id} data-testid={`audit-row-${r.id}`}>
              <td>{r.timestamp}</td>
              <td>{r.event_type}</td>
              <td>{r.subject_type}:{r.subject_id}</td>
              <td>{r.vendor_id ?? '—'}</td>
              <td>{r.source_ip ?? '—'}</td>
              <td>{r.action_detail ? JSON.stringify(r.action_detail) : '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>

      <div data-testid="pagination">
        <button disabled={page <= 1} onClick={() => setPage(p => p - 1)}>Prev</button>
        <span>Page {page}</span>
        <button disabled={page >= totalPages} onClick={() => setPage(p => p + 1)}>Next</button>
      </div>
    </section>
  )
}
