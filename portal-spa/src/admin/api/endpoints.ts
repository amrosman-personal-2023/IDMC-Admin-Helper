import { adminApi } from './client'

// ── Auth ──────────────────────────────────────────────────────────────────────
export interface AdminLoginResponse { logged_in: boolean; expires_at: string }
export const adminLogin = (username: string, password: string) =>
  adminApi.post<AdminLoginResponse>('/admin/auth/login', { username, password })
export const adminLogout = () => adminApi.post<void>('/admin/auth/logout')
export const adminValidate = () =>
  adminApi.post<{ valid: boolean; admin_id: number; role: string; expires_at: string }>(
    '/admin/auth/validate'
    // No body — the server reads the admin_session HttpOnly cookie directly.
    // JavaScript never touches the token value.
  )

// ── Dashboard ─────────────────────────────────────────────────────────────────
export interface DashboardStats {
  active_vendors: number
  enrolled_devices: number
  active_sessions: number
  audit_events_24h: number
  recent_audit: AuditRow[]
}
export const getDashboard = () => adminApi.get<DashboardStats>('/admin/dashboard')

// ── Vendors ───────────────────────────────────────────────────────────────────
export interface VendorRow {
  id: number; username: string; role: string
  created_at: string; active: boolean; device_count: number
}
export interface CreateVendorResponse {
  vendor_id: number; username: string; role: string
  otpauth_uri: string; qr_data_uri: string
}
export const listVendors = (page = 1, pageSize = 20) =>
  adminApi.get<VendorRow[]>(`/admin/vendors?page=${page}&page_size=${pageSize}`)
export const createVendor = (username: string, password: string, role: string) =>
  adminApi.post<CreateVendorResponse>('/admin/vendors', { username, password, role })
export const deactivateVendor = (id: number) =>
  adminApi.post<{ deactivated: boolean }>(`/admin/vendors/${id}/deactivate`)

// ── Devices ───────────────────────────────────────────────────────────────────
export interface DeviceRow {
  id: number; vendor_id: number; uuid_hash_suffix: string
  enrolled_at: string; revoked: boolean
  revoked_at: string | null; last_used_at: string | null
}
export interface ReissueResponse { vendor_id: number; otpauth_uri: string; qr_data_uri: string }
export const listDevices = (vendorId?: number) =>
  adminApi.get<DeviceRow[]>(vendorId != null ? `/admin/devices?vendor_id=${vendorId}` : '/admin/devices')
export const revokeDevice = (deviceUuid: string, vendorId: number) =>
  adminApi.post<{ revoked: boolean }>('/admin/devices/revoke', { device_uuid: deviceUuid, vendor_id: vendorId })
export const reissueEnrollmentLink = (vendorId: number) =>
  adminApi.post<ReissueResponse>('/admin/enrollment-links', { vendor_id: vendorId })

// ── Audit log ─────────────────────────────────────────────────────────────────
export interface AuditRow {
  id: number; event_type: string; subject_id: number; subject_type: string
  vendor_id: number | null; timestamp: string; source_ip: string | null
  action_detail: Record<string, unknown> | null
}
export interface AuditResponse { page: number; page_size: number; results: AuditRow[] }
export interface AuditFilters {
  vendor_id?: string; event_type?: string
  date_from?: string; date_to?: string
  page?: number; page_size?: number
}
export const getAuditLog = (filters: AuditFilters) => {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([k, v]) => { if (v != null && v !== '') params.set(k, String(v)) })
  return adminApi.get<AuditResponse>(`/admin/audit?${params}`)
}
export const exportAuditCsv = (filters: AuditFilters) => {
  const params = new URLSearchParams()
  Object.entries(filters).forEach(([k, v]) => { if (v != null && v !== '') params.set(k, String(v)) })
  return adminApi.getRaw(`/admin/audit?${params}`, { Accept: 'text/csv' })
}

// ── Log Analyser (backend API) ────────────────────────────────────────────────
export interface TreeEntry {
  name: string; path: string; type: 'file' | 'dir'
  size_bytes: number | null; modified_at: number
}
export interface LogRoot {
  name: string; label: string; path: string
}
export interface LogFile {
  path: string; content: string; lines: number; size_bytes: number
  service: string; directory: string; encoding: string; sensitive: boolean
}
export interface LlmSettings {
  provider: string; model: string; api_key_masked: string
  max_context_tokens: number; azure_endpoint: string; azure_deployment: string
}
export interface LogContext {
  file_path: string; content: string; service: string
  directory: string; lines: number; size_bytes: number
}

// No path → returns { roots: LogRoot[] }
// With path → returns { path: string; entries: TreeEntry[] }
export type LogTreeResponse =
  | { roots: LogRoot[] }
  | { path: string; entries: TreeEntry[] }

export const getLogTree = (path?: string) =>
  adminApi.get<LogTreeResponse>(
    `/admin/logs/tree${path ? `?path=${encodeURIComponent(path)}` : ''}`
  )

export const getLogFile = (path: string) =>
  adminApi.get<LogFile>(`/admin/logs/file?path=${encodeURIComponent(path)}`)

export const getLlmSettings = () => adminApi.get<LlmSettings>('/admin/llm/settings')

export const updateLlmSettings = (body: {
  provider: string; model: string; api_key: string; max_context_tokens: number
  azure_endpoint?: string; azure_deployment?: string
}) => adminApi.put<LlmSettings>('/admin/llm/settings', body)

export const testLlmConnection = () =>
  adminApi.post<{ success: boolean; latency_ms: number; response?: string; error?: string }>(
    '/admin/llm/test'
  )

// ── Allowed extensions (backend API) ─────────────────────────────────────────
export interface ExtensionsResponse { extensions: string[] }
export const getExtensions = () => adminApi.get<ExtensionsResponse>('/admin/extensions')
export const updateExtensions = (extensions: string[]) =>
  adminApi.put<ExtensionsResponse>('/admin/extensions', { extensions })

// ── Sessions ──────────────────────────────────────────────────────────────────
export interface SessionRow {
  id: number; subject_id: number; subject_type: string; role: string
  created_at: string; last_active_at: string; expires_at: string; source_ip: string | null
}
export const listSessions = () => adminApi.get<SessionRow[]>('/admin/sessions')
export const forceExpireSession = (id: number) =>
  adminApi.post<{ expired: boolean }>(`/admin/sessions/${id}/expire`)
