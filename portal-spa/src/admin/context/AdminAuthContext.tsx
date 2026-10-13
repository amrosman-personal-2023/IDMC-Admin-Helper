/**
 * Admin auth context — completely isolated from the vendor portal.
 * Stores no credentials in localStorage or sessionStorage.
 * The admin_session HttpOnly cookie is managed entirely by the server.
 */
import React, { createContext, useContext, useState, useCallback, useEffect } from 'react'
import { adminValidate } from '../api/endpoints'
import { AdminApiError } from '../api/client'

interface AdminAuthState {
  authenticated: boolean
  loading: boolean
  adminId: number | null
}

interface AdminAuthContextValue extends AdminAuthState {
  refresh: () => Promise<void>
  markLoggedOut: () => void
}

const AdminAuthContext = createContext<AdminAuthContextValue | null>(null)

export function AdminAuthProvider({ children }: { children: React.ReactNode }) {
  const [state, setState] = useState<AdminAuthState>({
    authenticated: false, loading: true, adminId: null,
  })

  const refresh = useCallback(async () => {
    setState(s => ({ ...s, loading: true }))
    try {
      const data = await adminValidate()
      setState({ authenticated: data.valid, loading: false, adminId: data.admin_id })
    } catch (err) {
      const status = err instanceof AdminApiError ? err.status : 0
      setState({ authenticated: false, loading: false, adminId: null })
    }
  }, [])

  const markLoggedOut = useCallback(() =>
    setState({ authenticated: false, loading: false, adminId: null }), [])

  useEffect(() => { refresh() }, []) // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <AdminAuthContext.Provider value={{ ...state, refresh, markLoggedOut }}>
      {children}
    </AdminAuthContext.Provider>
  )
}

export function useAdminAuth() {
  const ctx = useContext(AdminAuthContext)
  if (!ctx) throw new Error('useAdminAuth must be used inside AdminAuthProvider')
  return ctx
}
