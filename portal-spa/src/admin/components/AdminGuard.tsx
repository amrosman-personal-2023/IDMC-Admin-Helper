import React from 'react'
import { Navigate, useLocation } from 'react-router-dom'
import { useAdminAuth } from '../context/AdminAuthContext'

export default function AdminGuard({ children }: { children: React.ReactNode }) {
  const { authenticated, loading } = useAdminAuth()
  const location = useLocation()

  if (loading) return <p>Loading…</p>
  if (!authenticated) {
    return <Navigate to="/admin/login" state={{ from: location }} replace />
  }
  return <>{children}</>
}
